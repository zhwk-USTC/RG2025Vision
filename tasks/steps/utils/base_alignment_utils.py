"""
步骤工具函数模块（基于离散底盘指令）
包含各个步骤中经常复用的代码，如位姿定位、对齐控制等
"""

from typing import Optional, Tuple, Literal
import time
from vision import get_vision, CAM_KEY_TYPE
from core.logger import logger
from tasks.behaviors import base_move, base_rotate, base_stop
from tasks.debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory
from .vision_utils import VisionUtils

# ---------------------------
# 控制策略参数（可按实际调参）
# ---------------------------

# 平移误差阈值：小于该值认为在容差内
DEFAULT_TOLERANCE_XY = 0.02
# 角度误差阈值（弧度）
DEFAULT_TOLERANCE_YAW = 0.01

# 允许旋转的位移门槛：只有当 |e_x|、|e_y| 都小于该值才会旋转
ROT_GATE_XY = 0.08  # m

# 单次旋转脉冲时长（秒）
ROT_PULSE_SEC = 0.20

# 单次平移脉冲时长（秒）
MOVE_PULSE_SEC = 0.20

# 运动指令执行等待时长（秒）
MOVE_WAIT_SEC = 0.10


class AlignmentUtils:
    """对齐控制相关工具函数（离散底盘指令版）"""

    YAW_SIGN: int = -1

    @staticmethod
    def calculate_position_error(pose, target_z: float, target_x: float = 0.0, target_yaw: float = 0.0) -> Tuple[float, float, float]:
        """
        计算位置误差（相机系：x左、y上、z外）
        e_x: 前后距离误差（用 z）
        e_y: 左右误差（左正，取 -x）
        e_yaw: 平面朝向误差 —— 注意此处使用 pose.pitch 作为“平面yaw”
        """
        # 距离误差
        e_x = float(target_z) - float(pose.z)

        # 侧向误差
        e_y = float(target_x)- float(pose.x)

        import math
        yaw_diff = float(target_yaw) - float(pose.pitch)
        while yaw_diff > math.pi:
            yaw_diff -= 2 * math.pi
        while yaw_diff < -math.pi:
            yaw_diff += 2 * math.pi

        e_yaw = AlignmentUtils.YAW_SIGN * yaw_diff
        return e_x, e_y, e_yaw

    @staticmethod
    def is_aligned(
        e_x: float, e_y: float, e_yaw: float,
        tolerance_xy: float = DEFAULT_TOLERANCE_XY,
        tolerance_yaw: float = DEFAULT_TOLERANCE_YAW
    ) -> bool:
        return abs(e_x) < tolerance_xy and abs(e_y) < tolerance_xy and abs(e_yaw) < tolerance_yaw

    @staticmethod
    def _pick_speed_tag(mag: float, fast_thr: float) -> Literal['fast', 'slow']:
        return 'fast' if abs(mag) >= fast_thr else 'slow'

    @staticmethod
    def _move_discrete(e_x: float, e_y: float) -> None:
        """
        根据 e_x / e_y 误差发出一次“平移”离散指令。
        规则：
          - 优先纠正更大的绝对误差
          - e_x > 0（z 大于目标）→ backward；e_x < 0 → forward
          - e_y > 0（左偏）→ left；e_y < 0（右偏）→ right
        """
        ax, ay = abs(e_x), abs(e_y)

        if ax >= ay and ax > 0:
            # 优先纠正距离误差
            if e_x > 0:
                base_move('left_slow')     # 太远了 → 向左靠近
            else:
                base_move('right_slow')    # 太近了 → 向右远离
        elif ay > 0:
            if e_y > 0:
                base_move('forward_slow')
            else:
                base_move('backward_slow')
        else:
            # 误差很小，直接停止
            base_stop()
            return
        
        # 运动一段时间后停止
        time.sleep(MOVE_PULSE_SEC)  # 给足够时间让机器人真正移动
        base_stop()


    @staticmethod
    def _rotate_discrete(e_yaw: float) -> None:
        """
        极简旋转：角度误差超出容差就打一发慢速脉冲，然后停止。
        不做滞回/状态机。
        """
        ayaw = abs(e_yaw)
        if ayaw <= DEFAULT_TOLERANCE_YAW:
            return

        if e_yaw > 0:
            base_rotate('ccw_slow')
        else:
            base_rotate('cw_slow')

        time.sleep(ROT_PULSE_SEC)  # 短脉冲
        base_stop()

    @staticmethod
    def execute_alignment_move(e_x: float, e_y: float, e_yaw: float):
        """
        简化调度：
        - 只要线性误差超过容差，就做一次平移微调（slow 脉冲）
        - 仅当两轴线性误差都很小且角度超容差时才旋转
        - 其余情况停止
        """
        rot_thr = DEFAULT_TOLERANCE_YAW

        linear_err = max(abs(e_x), abs(e_y))

        # 1) 线性误差优先：超过线性容差就平移（无视 ROT_GATE_XY）
        if linear_err > DEFAULT_TOLERANCE_XY:
            AlignmentUtils._move_discrete(e_x, e_y)
            return

        # 2) 线性很小，再看角度：仅在两轴都 ≤ ROT_GATE_XY 且角度超容差时旋转
        if abs(e_x) <= ROT_GATE_XY and abs(e_y) <= ROT_GATE_XY and abs(e_yaw) > rot_thr:
            AlignmentUtils._rotate_discrete(e_yaw)
            return

        # 3) 都在容差附近：停
        base_stop()

    @staticmethod
    def apriltag_alignment_loop(
        cam_key: CAM_KEY_TYPE,
        target_tag_families: str,
        target_tag_id: Optional[int],
        target_z: float,
        debug_prefix: str,
        task_name: str,
        *,
        target_x: float = 0.0,
        target_yaw: float = 0.0,
        max_retries: int = 20
        
    ) -> bool:
        if not VisionUtils.check_vision_system(f'{debug_prefix}_error'):
            return False

        while True:
            det, pose = VisionUtils.detect_apriltag_with_retry(
                cam_key, 
                target_tag_families,
                target_tag_id, 
                max_retries, 
                0.05, 
                debug_prefix, 
                task_name
            )
            if pose is None:
                base_stop()
                return False

            e_x, e_y, e_yaw = AlignmentUtils.calculate_position_error(
                pose, target_z, target_x, target_yaw
            )
            
            # 添加详细的调试信息，包括原始pose值
            yaw_source = 'pitch' if hasattr(pose, 'pitch') and pose.pitch is not None else 'yaw'
            set_debug_var(
                f'{debug_prefix}_pose_raw',
                {
                    'x': round(float(pose.x), 3),
                    'z': round(float(pose.z), 3),
                    'pitch': round(float(getattr(pose, 'pitch', 0.0)), 3),
                    'yaw': round(float(getattr(pose, 'yaw', 0.0)), 3),
                    'yaw_used': yaw_source
                },
                DebugLevel.INFO, DebugCategory.POSITION, "检测到的原始pose值"
            )
            set_debug_var(
                f'{debug_prefix}_err',
                {'ex': round(e_x, 3), 'ey': round(e_y, 3), 'eyaw': round(e_yaw, 3)},
                DebugLevel.INFO, DebugCategory.POSITION, "与目标位置的误差"
            )

            if AlignmentUtils.is_aligned(e_x, e_y, e_yaw):
                base_stop()
                logger.info(f"[{task_name}] 已对齐到目标位置")
                set_debug_var(f'{debug_prefix}_status', 'done',
                              DebugLevel.SUCCESS, DebugCategory.STATUS, f"已成功对齐到{task_name}")
                break

            AlignmentUtils.execute_alignment_move(e_x, e_y, e_yaw)
            set_debug_var(f'{debug_prefix}_status', 'adjusting',
                          DebugLevel.INFO, DebugCategory.STATUS, f"正在调整位置对齐{task_name}")
            
            # 等待一段时间让运动完成，然后再进行下一次检测
            time.sleep(MOVE_WAIT_SEC)  # 短暂等待让运动指令完全执行

        return True

# 便捷函数
def base_align_to_apriltag(
    cam_key: CAM_KEY_TYPE, 
    target_tag_families: str,
    target_tag_id: Optional[int], 
    target_z: float,
    debug_prefix: str, task_name: str,
    target_x: float = 0.0,
    target_yaw: float = 0.0
) -> bool:
    return AlignmentUtils.apriltag_alignment_loop(
        cam_key, 
        target_tag_families,
        target_tag_id, 
        target_z, 
        debug_prefix, 
        task_name,
        target_x=target_x,
        target_yaw=target_yaw
    )

