"""
步骤工具函数模块（基于离散底盘指令）
包含各个步骤中经常复用的代码，如位姿定位、对齐控制等
"""

from typing import Optional, Dict, Any, Tuple, Union, Literal
import time
from vision import get_vision, CAM_KEY_TYPE
from core.logger import logger
from ..behaviors import base_move, base_rotate, base_stop
from ..debug_vars_enhanced import set_debug_var, set_debug_image, DebugLevel, DebugCategory

# 定义相机键名类型
CameraKey = CAM_KEY_TYPE

# ---------------------------
# 控制策略参数（可按实际调参）
# ---------------------------

# 平移误差阈值：小于该值认为在容差内
DEFAULT_TOLERANCE_XY = 0.02
# 角度误差阈值（弧度）
DEFAULT_TOLERANCE_YAW = 0.02

# 允许旋转的位移门槛：只有当 |e_x|、|e_y| 都小于该值才会旋转
ROT_GATE_XY = 0.08  # m

# 单次旋转脉冲时长（秒）
ROT_PULSE_SEC = 0.20

# 单次平移脉冲时长（秒）
MOVE_PULSE_SEC = 0.30

# 运动指令执行等待时长（秒）
MOVE_WAIT_SEC = 0.10

class VisionUtils:
    """视觉相关工具函数"""

    @staticmethod
    def check_vision_system(error_prefix: str = "vision_error") -> bool:
        vs = get_vision()
        if not vs:
            set_debug_var(error_prefix, 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return False
        return True

    @staticmethod
    def get_frame_safely(
        cam_key: CameraKey,
        error_prefix: str = "frame_error",
        debug_image_key: Optional[str] = None,
        debug_description: str = ""
    ):
        vs = get_vision()
        if not vs:
            return None

        # 检查并连接摄像头
        cam = vs._cameras.get(cam_key)
        if cam is None:
            set_debug_var(error_prefix, 'camera not found', DebugLevel.ERROR, DebugCategory.ERROR, f"未找到摄像头 {cam_key}")
            return None
        
        if not cam.is_open:
            logger.info(f"[VisionUtils] 摄像头 {cam_key} 未连接，正在连接...")
            if not cam.connect():
                set_debug_var(error_prefix, 'camera connect failed', DebugLevel.ERROR, DebugCategory.ERROR, f"摄像头 {cam_key} 连接失败")
                return None
            logger.info(f"[VisionUtils] 摄像头 {cam_key} 连接成功")

        try:
            frame = vs.read_frame(cam_key)  # type: ignore
            if frame is None:
                set_debug_var(error_prefix, 'empty frame', DebugLevel.ERROR, DebugCategory.ERROR, "无法获取相机帧")
                return None

            if debug_image_key:
                set_debug_image(debug_image_key, frame, debug_description)
            return frame
        except RuntimeError as e:
            set_debug_var(error_prefix, f'read frame error: {str(e)}', DebugLevel.ERROR, DebugCategory.ERROR, f"读取相机帧失败: {str(e)}")
            return None

    @staticmethod
    def detect_apriltag_with_retry(
        cam_key: CameraKey,
        target_tag_families: str,
        target_tag_id: Optional[int] = None,
        max_retries: int = 20,
        retry_delay: float = 0.05,
        debug_prefix: str = "tag",
        debug_description: str = "标签检测"
    ):
        vs = get_vision()
        if not vs:
            set_debug_var(f'{debug_prefix}_error', 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return None, None

        iter_cnt = 0
        while iter_cnt <= max_retries:
            frame = VisionUtils.get_frame_safely(
                cam_key,
                f'{debug_prefix}_error',
                f'{debug_prefix}_frame',
                f"{debug_description}时的相机帧"
            )
            if frame is None:
                return None, None

            intr = vs.get_camera_intrinsics(cam_key)  # type: ignore
            if(target_tag_families == 'tag36h11'):
                dets = vs.detect_tag36h11(frame, intr)
            elif target_tag_families == 'tag25h9':
                dets = vs.detect_tag25h9(frame, intr)
            else:
                set_debug_var(f'{debug_prefix}_error', 'unknown tag family', DebugLevel.ERROR, DebugCategory.ERROR, f"未知的标签族: {target_tag_families}")
                return None, None
            set_debug_var(f'{debug_prefix}_detections', len(dets) if dets else 0,
                          DebugLevel.INFO, DebugCategory.DETECTION, f"检测到的{debug_description}数量")

            if not dets:
                if iter_cnt >= max_retries:
                    logger.error(f"[{debug_description}] 未检测到标签")
                    set_debug_var(f'{debug_prefix}_error', 'no tag found',
                                  DebugLevel.ERROR, DebugCategory.DETECTION, f"未检测到{debug_description}")
                    return None, None
                iter_cnt += 1
                time.sleep(retry_delay)
                continue

            # 选择目标标签
            if target_tag_id is None:
                det = dets[0]  # 未指定ID时选择第一个
            else:
                # 指定了ID时，必须找到对应的标签
                det = next((d for d in dets if getattr(d, 'tag_id', None) == target_tag_id), None)
                if det is None:
                    if iter_cnt >= max_retries:
                        logger.error(f"[{debug_description}] 未找到指定ID={target_tag_id}的标签")
                        set_debug_var(f'{debug_prefix}_error', f'target tag {target_tag_id} not found',
                                      DebugLevel.ERROR, DebugCategory.DETECTION, f"未找到指定{debug_description}ID={target_tag_id}")
                        return None, None
                    iter_cnt += 1
                    time.sleep(retry_delay)
                    continue
            set_debug_var(f'{debug_prefix}_tag_id', getattr(det, 'tag_id', None),
                          DebugLevel.INFO, DebugCategory.DETECTION, f"当前检测到的{debug_description}ID")

            pose = vs.locate_from_tag(det)
            if pose is None:
                logger.error(f"[{debug_description}] 无法从标签中定位")
                set_debug_var(f'{debug_prefix}_error', 'pose none',
                              DebugLevel.ERROR, DebugCategory.POSITION, "无法从标签获取位姿信息")
                return None, None

            return det, pose

        return None, None


class AlignmentUtils:
    """对齐控制相关工具函数（离散底盘指令版）"""

    YAW_SIGN: int = +1

    # 内部状态：用于旋转的滞回与效果监测
    _rotating: bool = False
    _last_yaw_mag: float | None = None
    _no_improve_cnt: int = 0
    
    # 自适应旋转控制：记录上一次的角度误差，检测是否在发散
    _last_e_yaw: float | None = None
    _consecutive_same_direction: int = 0
    _max_consecutive_same_direction: int = 5  # 连续同方向旋转次数阈值
    
    @staticmethod
    def calculate_position_error(pose, target_z: float, target_x: float = 0.0, target_yaw: float = 0.0) -> Tuple[float, float, float]:
        """
        计算位置误差（相机系：x右、y下、z里）
        e_x: 前后距离误差（用 z）
        e_y: 左右误差（左正，取 -x）
        e_yaw: 平面朝向误差 —— 注意此处使用 pose.pitch 作为“平面yaw”
        """
        # 距离误差：以 z 表示前向距离
        actual_distance = abs(float(pose.z))
        e_x = actual_distance - float(target_z)

        # 侧向误差：左正 → -x
        e_y = -float(getattr(pose, 'x', 0.0)) - 0.0  # target_x 若用于其它任务，可在此叠加

        # ====== 关键修正：把 pitch 作为“平面上的 yaw” ======
        raw_yaw = None
        if hasattr(pose, 'pitch') and pose.pitch is not None:
            raw_yaw = float(pose.pitch)
            yaw_source = 'pitch'
        else:
            # 兼容：若暂时没有 pitch 字段，回退到旧的 yaw 字段
            raw_yaw = float(getattr(pose, 'yaw', 0.0))
            yaw_source = 'yaw(fallback)'

        # 与目标朝向（target_yaw）之差，并规范到 [-pi, pi]
        import math
        yaw_diff = raw_yaw - float(target_yaw)
        yaw_diff_before_norm = yaw_diff
        while yaw_diff > math.pi:
            yaw_diff -= 2 * math.pi
        while yaw_diff < -math.pi:
            yaw_diff += 2 * math.pi

        e_yaw = AlignmentUtils.YAW_SIGN * yaw_diff

        # 调试输出
        set_debug_var('yaw_calc_source', yaw_source, DebugLevel.INFO, DebugCategory.POSITION, "用于平面朝向的字段")
        set_debug_var('yaw_calc_raw', round(raw_yaw, 3), DebugLevel.INFO, DebugCategory.POSITION, f"原始角度({yaw_source})")
        set_debug_var('yaw_calc_target', round(float(target_yaw), 3), DebugLevel.INFO, DebugCategory.POSITION, "目标yaw角度")
        set_debug_var('yaw_calc_diff_before', round(yaw_diff_before_norm, 3), DebugLevel.INFO, DebugCategory.POSITION, "标准化前差值")
        set_debug_var('yaw_calc_diff_after', round(yaw_diff, 3), DebugLevel.INFO, DebugCategory.POSITION, "标准化后差值")
        set_debug_var('yaw_calc_sign', AlignmentUtils.YAW_SIGN, DebugLevel.INFO, DebugCategory.POSITION, "YAW_SIGN")
        set_debug_var('yaw_calc_final', round(e_yaw, 3), DebugLevel.INFO, DebugCategory.POSITION, "最终误差e_yaw")

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
                base_move('backward_slow')
            else:
                base_move('forward_slow')
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
        cam_key: CameraKey,
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


class CustomDetectionUtils:
    """自定义检测相关工具函数"""

    @staticmethod
    def detect_with_retry(
        detection_func, frame_getter, error_handler,
        max_retries: int = 20, retry_delay: float = 0.05,
        debug_prefix: str = "detection"
    ) -> Any:
        iter_cnt = 0
        while iter_cnt <= max_retries:
            frame = frame_getter()
            if frame is None:
                return None

            result = detection_func(frame)
            if result is not None:
                return result

            if iter_cnt >= max_retries:
                error_handler(debug_prefix)
                return None

            iter_cnt += 1
            time.sleep(retry_delay)

        return None

    @staticmethod
    def custom_detection_alignment_loop(
        cam_key: CameraKey, detection_func, target_distance: float,
        debug_prefix: str, task_name: str, max_retries: int = 20
    ) -> bool:
        if not VisionUtils.check_vision_system(f'{debug_prefix}_error'):
            return False

        iter_cnt = 0
        while True:
            frame = VisionUtils.get_frame_safely(
                cam_key, f'{debug_prefix}_error', f'{debug_prefix}_frame', f"{task_name}时的相机帧"
            )
            if frame is None:
                base_stop()
                return False

            detection_result = detection_func(frame)
            if detection_result is None:
                if iter_cnt >= max_retries:
                    base_stop()
                    logger.error(f"[{task_name}] 未检测到目标")
                    set_debug_var(f'{debug_prefix}_error', 'no target found',
                                  DebugLevel.ERROR, DebugCategory.DETECTION, f"未检测到{task_name}目标")
                    return False
                iter_cnt += 1
                time.sleep(MOVE_WAIT_SEC)  # 检测失败时等待足够时间再重试
                continue

            set_debug_var(f'{debug_prefix}_target_pos', detection_result,
                          DebugLevel.INFO, DebugCategory.DETECTION, "检测到的目标位置")

            e_x = detection_result.get('x', 0) - target_distance
            e_y = detection_result.get('y', 0)
            e_yaw = detection_result.get('yaw', 0)

            set_debug_var(
                f'{debug_prefix}_err',
                {'ex': round(e_x, 3), 'ey': round(e_y, 3), 'eyaw': round(e_yaw, 3)},
                DebugLevel.INFO, DebugCategory.POSITION, "与目标位置的误差"
            )

            if AlignmentUtils.is_aligned(e_x, e_y, e_yaw):
                base_stop()
                logger.info(f"[{task_name}] 已对齐到目标")
                set_debug_var(f'{debug_prefix}_status', 'aligned',
                              DebugLevel.SUCCESS, DebugCategory.STATUS, f"已成功对齐到{task_name}")
                break

            AlignmentUtils.execute_alignment_move(e_x, e_y, e_yaw)
            set_debug_var(f'{debug_prefix}_status', 'adjusting',
                          DebugLevel.INFO, DebugCategory.STATUS, f"正在调整{task_name}位置")
            
            # 等待一段时间让运动完成，然后再进行下一次检测
            time.sleep(MOVE_WAIT_SEC)  # 短暂等待让运动指令完全执行

        return True


# 便捷函数
def align_to_apriltag(
    cam_key: CameraKey, 
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


def align_to_custom_target(
    cam_key: CameraKey, detection_func, target_distance: float,
    debug_prefix: str, task_name: str
) -> bool:
    return CustomDetectionUtils.custom_detection_alignment_loop(
        cam_key, detection_func, target_distance, debug_prefix, task_name
    )
