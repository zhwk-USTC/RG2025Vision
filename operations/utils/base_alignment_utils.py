"""
步骤工具函数模块（基于离散底盘指令）
包含各个步骤中经常复用的代码，如位姿定位、对齐控制等
"""

from typing import Optional, Tuple, Literal, List
import time
from vision import CAM_KEY_TYPE
from core.logger import logger
from ..debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory
from .vision_utils import VisionUtils
from .base_movement_utils import MovementUtils, MoveDirection

# ---------------------------
# 控制策略参数（可按实际调参）
# ---------------------------

# 平移误差阈值：小于该值认为在容差内
DEFAULT_TOLERANCE_XY = 0.005
# 角度误差阈值（弧度）
DEFAULT_TOLERANCE_YAW = 0.01

# 允许旋转的位移门槛
ROT_GATE_TOLERANCE_M = 0.10

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
        tolerance_x: float = DEFAULT_TOLERANCE_XY,
        tolerance_z: float = DEFAULT_TOLERANCE_XY,
        tolerance_yaw: float = DEFAULT_TOLERANCE_YAW
    ) -> bool:
        # e_x 对应 z 轴误差（前后），e_y 对应 x 轴误差（左右）
        return abs(e_x) < tolerance_z and abs(e_y) < tolerance_x and abs(e_yaw) < tolerance_yaw
    
    @staticmethod
    def get_move_dir(e_x: float, e_y: float, cam_key: CAM_KEY_TYPE) -> MoveDirection:
        """
        根据误差和相机类型生成移动命令

        参数:
            e_x: X轴误差（前后，e_x > 0 表示需要向前移动）
            e_y: Y轴误差（左右，e_y > 0 表示需要向左移动）
            cam_key: 相机键名 ("front" 或 "left")
            is_fast: 是否使用快速移动

        返回:
            移动命令，或 None（如果没有有效误差）
        """
        ax, ay = abs(e_x), abs(e_y)

        # 选主轴（优先纠正更大的绝对误差）
        use_x = (ax >= ay)

        # 根据相机类型和误差方向选择移动命令
        if cam_key == "front":
            # 前方相机的移动逻辑
            if use_x:
                if e_x > 0:
                    return 'forward'
                else:
                    return 'backward'
            else:
                if e_y > 0:
                    return 'right'
                else:
                    return 'left'
        else:
            # left 相机的移动逻辑（默认）
            if use_x:
                if e_x > 0:
                    return 'left'
                else:
                    return 'right'
            else:
                if e_y > 0:
                    return 'forward'
                else:
                    return 'backward'

    @staticmethod
    def _move_discrete(e_x: float, e_y: float, cam_key: CAM_KEY_TYPE) -> None:
        """
        根据 e_x / e_y 误差发出一次“平移”离散指令（动态脉冲时长）。
        """
        mag = max(abs(e_x), abs(e_y))
        move_dir: MoveDirection = AlignmentUtils.get_move_dir(e_x, e_y, cam_key)
        if move_dir:
            MovementUtils.execute_move_by_distance(move_dir, mag)

    @staticmethod
    def _rotate_discrete(e_yaw: float) -> None:
        """
        角度误差超出容差即打一发“动态脉冲”。
        """
        MovementUtils.execute_rotate_by_angle(e_yaw)

    @staticmethod
    def execute_alignment_move(
        e_x: float, e_y: float, e_yaw: float, cam_key: CAM_KEY_TYPE,
        tolerance_x: float = DEFAULT_TOLERANCE_XY,
        tolerance_z: float = DEFAULT_TOLERANCE_XY,
        tolerance_yaw: float = DEFAULT_TOLERANCE_YAW
    ):
        """
        智能调度策略：
        - 角度误差较大时（>ANGLE_PRIORITY_THRESHOLD），优先处理角度
        - 角度误差较小时，优先处理位置，位置对齐后再处理角度
        - 避免在错误朝向下进行位置调整，提高对齐效率
        """
        # e_x 对应 z 轴误差（前后），e_y 对应 x 轴误差（左右）
        ax = abs(e_y)
        az = abs(e_x)
        ayaw = abs(e_yaw)
        x_aligned = ax <= tolerance_x  # 左右对齐
        z_aligned = az <= tolerance_z  # 前后对齐
        yaw_aligned = ayaw <= tolerance_yaw  # 角度对齐

        rotation_gate_x = max(ROT_GATE_TOLERANCE_M, tolerance_x)
        rotation_gate_z = max(ROT_GATE_TOLERANCE_M, tolerance_z)
        
        in_rot_gate = (ax <= rotation_gate_x) and (az <= rotation_gate_z)
        # 没有在旋转门槛内，优先移动
        if not in_rot_gate:
            AlignmentUtils._move_discrete(e_x, e_y, cam_key)
            return
        # 在旋转门槛内，优先旋转
        elif not yaw_aligned:
            AlignmentUtils._rotate_discrete(e_yaw)
            return
        # 位置和角度都在门槛内，优先位置微调
        else:
            if not (x_aligned and z_aligned):
                AlignmentUtils._move_discrete(e_x, e_y, cam_key)
                return

        MovementUtils.stop_movement()

    @staticmethod
    def apriltag_alignment_loop(
        cam_key: CAM_KEY_TYPE,
        target_tag_families: str,
        target_tag_ids: Optional[List[int]],      # 改：使用列表
        target_tag_size: Optional[float],
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
        # 归一化：确保是 List[int]；空列表按 None 处理
        ids_norm: Optional[List[int]] = None
        if target_tag_ids is not None:
            try:
                ids_norm = [int(x) for x in target_tag_ids]
                if len(ids_norm) == 0:
                    ids_norm = None
            except Exception:
                ids_norm = None  # 非法内容时视为未指定

        if not VisionUtils.check_vision_system(f'{debug_prefix}_error'):
            return False

        while True:
            det, pose = VisionUtils.detect_apriltag_with_retry(
                cam_key=cam_key,
                target_tag_families=target_tag_families,
                target_tag_ids=ids_norm,                 # 改：传入列表
                target_tag_size=target_tag_size,
                max_retries=max_retries,
                retry_delay=0.05,
                debug_prefix=debug_prefix,
                debug_description=task_name
            )
            if pose is None:
                MovementUtils.stop_movement()
                return False

            e_x, e_y, e_yaw = AlignmentUtils.calculate_position_error(
                pose, target_z, target_x, target_yaw
            )

            # 调试：记录 pose 与误差
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
                MovementUtils.stop_movement()
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
    target_tag_ids: Optional[List[int]], 
    target_tag_size: float,
    target_z: float,
    target_x: float = 0.0,
    target_yaw: float = 0.0,
    tolerance_x: float = DEFAULT_TOLERANCE_XY,
    tolerance_z: float = DEFAULT_TOLERANCE_XY,
    tolerance_yaw: float = DEFAULT_TOLERANCE_YAW
) -> bool:
    """
    基于AprilTag的底盘对齐函数（支持多个 ID）
    """
    # 直接把列表传给 alignment_loop；归一化逻辑在内部完成
    return AlignmentUtils.apriltag_alignment_loop(
        cam_key=cam_key, 
        target_tag_families=target_tag_families,
        target_tag_ids=target_tag_ids,
        target_tag_size=target_tag_size,
        target_z=target_z, 
        debug_prefix="tag_align",
        task_name="TagAlign",
        target_x=target_x,
        target_yaw=target_yaw,
        tolerance_x=tolerance_x,
        tolerance_z=tolerance_z,
        tolerance_yaw=tolerance_yaw
    )
