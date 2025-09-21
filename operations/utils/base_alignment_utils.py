"""
步骤工具函数模块（基于离散底盘指令）
包含各个步骤中经常复用的代码，如位姿定位、对齐控制等
"""

from typing import Optional, Tuple, Literal
import time
from vision import get_vision, CAM_KEY_TYPE
from core.logger import logger
from .communicate_utils import base_move, base_rotate, base_stop
from ..debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory
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
MOVE_PULSE_MAX_SEC = 2.00
# 旋转脉冲最小/最大时长（秒）
ROT_PULSE_MIN_SEC  = 0.05
ROT_PULSE_MAX_SEC  = 2.00

# 速度参数（米/秒）
SLOW_SPEED_MPS = 0.1    # 慢速移动速度
FAST_SPEED_MPS = 0.3    # 快速移动速度
# 旋转速度参数（弧度/秒，估算）
SLOW_ROT_SPEED_RPS = 0.2    # 慢速旋转角速度  
FAST_ROT_SPEED_RPS = 0.6    # 快速旋转角速度

# 当误差超过该阈值时使用“fast”速度档，否则“slow”
MOVE_FAST_THR_M = 0.12      # 平移快慢阈值（m）
ROT_FAST_THR_RAD = 0.20     # 旋转快慢阈值（rad）

# 运动指令执行等待时长（秒）——基线（最终会在代码里与动态脉冲叠加）
MOVE_WAIT_BASE_SEC = 0.5

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
        # 叠加一点与脉冲相关的“完成等待”
        settle = MOVE_WAIT_BASE_SEC
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
        tolerance_x: float = DEFAULT_TOLERANCE_XY,
        tolerance_z: float = DEFAULT_TOLERANCE_XY,
        tolerance_yaw: float = DEFAULT_TOLERANCE_YAW
    ) -> bool:
        # e_x 对应 z 轴误差（前后），e_y 对应 x 轴误差（左右）
        return abs(e_x) < tolerance_z and abs(e_y) < tolerance_x and abs(e_yaw) < tolerance_yaw

    @staticmethod
    def _move_discrete(e_x: float, e_y: float, cam_key: CAM_KEY_TYPE) -> None:
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

        # 根据误差大小选择快慢速度
        is_fast = mag > MOVE_FAST_THR_M
        speed = FAST_SPEED_MPS if is_fast else SLOW_SPEED_MPS
        
        # 脉冲时长 = 距离 / 速度
        raw_pulse = float(mag) / speed
        pulse_sec = max(MOVE_PULSE_MIN_SEC, min(MOVE_PULSE_MAX_SEC, raw_pulse))

        # ---- 根据误差大小选择快慢速度档位 ----
        if cam_key == "front":
    # 前方相机的移动逻辑
            if use_x:
                if e_x > 0:
                    base_move('forward_fast' if is_fast else 'forward_slow')
                else:
                    base_move('backward_fast' if is_fast else 'backward_slow')
            else:
                if e_y > 0:
                    base_move('left_fast' if is_fast else 'left_slow')
                else:
                    base_move('right_fast' if is_fast else 'right_slow')
        else:
            # left 相机的移动逻辑（默认）
            if use_x:
                if e_x > 0:
                    base_move('left_fast' if is_fast else 'left_slow')
                else:
                    base_move('right_fast' if is_fast else 'right_slow')
            else:
                if e_y > 0:
                    base_move('forward_fast' if is_fast else 'forward_slow')
                else:
                    base_move('backward_fast' if is_fast else 'backward_slow')
                
        AlignmentUtils._sleep_and_stop(pulse_sec)


    @staticmethod
    def _rotate_discrete(e_yaw: float, tolerance_yaw: float = DEFAULT_TOLERANCE_YAW) -> None:
        """
        角度误差超出容差即打一发“动态脉冲”。
        """
        ayaw = abs(e_yaw)
        if ayaw <= tolerance_yaw:
            return

        # 根据角度误差大小选择快慢速度
        is_fast = False
        rot_speed = FAST_ROT_SPEED_RPS if is_fast else SLOW_ROT_SPEED_RPS
        
        # 脉冲时长 = 角度 / 角速度
        raw_pulse = float(ayaw) / rot_speed
        pulse_sec = max(ROT_PULSE_MIN_SEC, min(ROT_PULSE_MAX_SEC, raw_pulse))

        speed_suffix = '_fast' if is_fast else '_slow'
        
        if e_yaw > 0:
            base_rotate('ccw_fast' if is_fast else 'ccw_slow')
        else:
            base_rotate('cw_fast' if is_fast else 'cw_slow')
        
        AlignmentUtils._sleep_and_stop(pulse_sec)

    @staticmethod
    def execute_alignment_move(
        e_x: float, e_y: float, e_yaw: float, cam_key: CAM_KEY_TYPE,
        tolerance_x: float = DEFAULT_TOLERANCE_XY,
        tolerance_z: float = DEFAULT_TOLERANCE_XY,
        tolerance_yaw: float = DEFAULT_TOLERANCE_YAW
    ):
        """
        简化调度：
        - 只要线性误差超过容差，就做一次平移微调（动态脉冲）
        - 仅当两轴线性误差都很小且角度超容差时才旋转（动态脉冲）
        - 其余情况停止
        """
        # e_x 对应 z 轴误差（前后），e_y 对应 x 轴误差（左右）
        x_aligned = abs(e_y) <= tolerance_x  # 左右对齐
        z_aligned = abs(e_x) <= tolerance_z  # 前后对齐
        
        if not (x_aligned and z_aligned):
            AlignmentUtils._move_discrete(e_x, e_y, cam_key)
            return

        if x_aligned and z_aligned and abs(e_yaw) > tolerance_yaw:
            # 只有当位置都对齐且在旋转门槛内时才旋转
            if abs(e_x) <= ROT_GATE_XY and abs(e_y) <= ROT_GATE_XY:
                AlignmentUtils._rotate_discrete(e_yaw, tolerance_yaw)
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
        tolerance_x: float = DEFAULT_TOLERANCE_XY,
        tolerance_z: float = DEFAULT_TOLERANCE_XY,
        tolerance_yaw: float = DEFAULT_TOLERANCE_YAW,
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

            if AlignmentUtils.is_aligned(
                e_x, e_y, e_yaw,
                tolerance_x=tolerance_x,
                tolerance_z=tolerance_z,
                tolerance_yaw=tolerance_yaw
            ):
                base_stop()
                logger.info(f"[{task_name}] 已对齐到目标位置")
                set_debug_var(f'{debug_prefix}_status', 'done',
                              DebugLevel.SUCCESS, DebugCategory.STATUS, f"已成功对齐到{task_name}")
                break

            AlignmentUtils.execute_alignment_move(
                e_x, e_y, e_yaw, cam_key,
                tolerance_x=tolerance_x,
                tolerance_z=tolerance_z,
                tolerance_yaw=tolerance_yaw
            )
            set_debug_var(f'{debug_prefix}_status', 'adjusting',
                          DebugLevel.INFO, DebugCategory.STATUS, f"正在调整位置对齐{task_name}")

        return True

# 便捷函数
def base_align_to_apriltag(
    cam_key: CAM_KEY_TYPE, 
    target_tag_families: str,
    target_tag_id: Optional[int], 
    target_z: float,
    target_x: float = 0.0,
    target_yaw: float = 0.0,
    tolerance_x: float = DEFAULT_TOLERANCE_XY,
    tolerance_z: float = DEFAULT_TOLERANCE_XY,
    tolerance_yaw: float = DEFAULT_TOLERANCE_YAW
) -> bool:
    """
    基于AprilTag的底盘对齐函数
    
    轴方向说明（相机坐标系）：
    - X轴：左右方向（左正右负）
    - Y轴：上下方向（上正下负，本函数中不使用）
    - Z轴：前后方向（远正近负）
    - Yaw：平面旋转角度（逆时针正，顺时针负）
    
    参数说明：
    - target_x: 目标X轴位置（左右偏移）
    - target_z: 目标Z轴位置（前后距离）
    - target_yaw: 目标Yaw角度（平面朝向）
    - tolerance_x: X轴允许误差（左右容差）
    - tolerance_z: Z轴允许误差（前后容差）
    - tolerance_yaw: Yaw角度允许误差
    """
    return AlignmentUtils.apriltag_alignment_loop(
        cam_key, 
        target_tag_families,
        target_tag_id, 
        target_z, 
        debug_prefix="tag_align",
        task_name="TagAlign",
        target_x=target_x,
        target_yaw=target_yaw,
        tolerance_x=tolerance_x,
        tolerance_z=tolerance_z,
        tolerance_yaw=tolerance_yaw
    )