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
DEFAULT_TOLERANCE_XY = 0.005
# 角度误差阈值（弧度）
DEFAULT_TOLERANCE_YAW = 0.01

# 允许旋转的位移门槛：只有当 |e_x|、|e_y| 都小于该值才会旋转
ROT_GATE_XY = 0.08  # m

# 平移脉冲最小/最大时长（秒）
MOVE_PULSE_MIN_SEC = 0.05
MOVE_PULSE_MAX_SEC = 1.00
# 旋转脉冲最小/最大时长（秒）
ROT_PULSE_MIN_SEC  = 0.05
ROT_PULSE_MAX_SEC  = 1.00

# 线性误差→时长 的增益（秒/米），例如 1 m 误差→0.35~0.4 s 脉冲
MOVE_GAIN_SEC_PER_M = 6.0
# 角度误差→时长 的增益（秒/弧度），例如 1 rad 误差→约 0.3 s 脉冲
ROT_GAIN_SEC_PER_RAD = 5.0

# 当误差超过该阈值时使用“fast”速度档，否则“slow”
MOVE_FAST_THR_M = 0.12      # 平移快慢阈值（m）
ROT_FAST_THR_RAD = 0.20     # 旋转快慢阈值（rad）

# 运动指令执行等待时长（秒）——基线（最终会在代码里与动态脉冲叠加）
MOVE_WAIT_BASE_SEC = 0.1

class AlignmentUtils:
    """对齐控制相关工具函数（离散底盘指令版）"""

    YAW_SIGN: int = -1

    @staticmethod
    def _sleep_and_stop(pulse_sec: float):
        """
        执行脉冲后等待，再停止。等待时长随脉冲动态放大，减少“没走完就测”的抖动。
        """
        # 主脉冲
        time.sleep(max(0.0, pulse_sec))
        base_stop()
        # 叠加一点与脉冲相关的“完成等待”（比例系数可按实际调）
        settle = MOVE_WAIT_BASE_SEC + 0.25 * pulse_sec
        time.sleep(settle)

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
    def _move_discrete(e_x: float, e_y: float) -> None:
        """
        根据 e_x / e_y 误差发出一次“平移”离散指令（动态脉冲时长）。
        —— 保持原有方向逻辑不变：
        * 优先纠正更大的绝对误差
        * e_x > 0 → left_slow；e_x < 0 → right_slow
        * e_y > 0 → forward_slow；e_y < 0 → backward_slow
        """
        ax, ay = abs(e_x), abs(e_y)

        # 选主轴（保持原逻辑：ax >= ay 时走 e_x 分支，否则走 e_y 分支）
        use_x = (ax >= ay)
        mag = ax if use_x else ay

        if mag <= 0.0:
            base_stop()
            return

        # ---- 动态脉冲时长：按误差幅值缩放，并夹到 [最小, 最大] ----
        raw_pulse = MOVE_GAIN_SEC_PER_M * float(mag)
        pulse_sec = max(MOVE_PULSE_MIN_SEC, min(MOVE_PULSE_MAX_SEC, raw_pulse))

        # ---- 保持“原方向映射”完全不变 ----
        if use_x:
            if e_x > 0:
                base_move('left_slow')
            else:
                base_move('right_slow')
        else:
            if e_y > 0:
                base_move('forward_slow')
            else:
                base_move('backward_slow')

        # 动态运动一段时间后停止
        time.sleep(pulse_sec)
        base_stop()


    @staticmethod
    def _rotate_discrete(e_yaw: float) -> None:
        """
        角度误差超出容差即打一发“动态脉冲”。
        """
        ayaw = abs(e_yaw)
        if ayaw <= DEFAULT_TOLERANCE_YAW:
            return

        # 动态脉冲：角度 * 增益 → [MIN, MAX]
        raw_pulse = ROT_GAIN_SEC_PER_RAD * float(ayaw)
        pulse_sec = max(ROT_PULSE_MIN_SEC, min(ROT_PULSE_MAX_SEC, raw_pulse))

        if e_yaw > 0:
            base_rotate('ccw_slow')
        else:
            base_rotate('cw_slow')

        AlignmentUtils._sleep_and_stop(pulse_sec)

    @staticmethod
    def execute_alignment_move(e_x: float, e_y: float, e_yaw: float):
        """
        简化调度：
        - 只要线性误差超过容差，就做一次平移微调（动态脉冲）
        - 仅当两轴线性误差都很小且角度超容差时才旋转（动态脉冲）
        - 其余情况停止
        """
        rot_thr = DEFAULT_TOLERANCE_YAW
        linear_err = max(abs(e_x), abs(e_y))

        if linear_err > DEFAULT_TOLERANCE_XY:
            AlignmentUtils._move_discrete(e_x, e_y)
            return

        if abs(e_x) <= ROT_GATE_XY and abs(e_y) <= ROT_GATE_XY and abs(e_yaw) > rot_thr:
            AlignmentUtils._rotate_discrete(e_yaw)
            return

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

