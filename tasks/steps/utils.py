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
DEFAULT_TOLERANCE_XY = 0.05
# 角度误差阈值（弧度）
DEFAULT_TOLERANCE_YAW = 0.1

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

            det = dets[0] if target_tag_id is None else next(
                (d for d in dets if getattr(d, 'tag_id', None) == target_tag_id), dets[0])
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

    # 如果发现旋转方向相反，把这个设为 -1
    YAW_SIGN = +1
    
    @staticmethod
    def calculate_position_error(pose, target_z: float, target_x: float = 0.0, target_yaw: float = 0.0) -> Tuple[float, float, float]:
        """
        计算位置误差（摄像头在机器人左侧）
        
        坐标系说明：
        - pose.x: tag右侧为正（相机在tag右侧时为正值）  
        - pose.z: tag内侧为正（通常为负数，相机在tag外侧）
        - target_z: 期望距离（正数）
        
        机器人运动映射：
        - 要靠近tag：向左移动（减小距离）
        - 要远离tag：向右移动（增大距离）
        - 前后移动：调整机器人与tag的前后位置关系
        
        Args:
            pose: 检测到的tag位姿
            target_z: 期望距离（正数，如0.5米）
            target_x: 相对tag坐标系的目标x位置（右为正）
            target_yaw: 相对tag坐标系的目标偏航角（弧度）
            
        Returns:
            (e_x, e_y, e_yaw): 前后误差、左右误差、偏航误差
        """
            
        # 左右误差：控制机器人与tag的距离
        # pose.z通常为负数，|pose.z|是实际距离
        actual_distance = abs(float(pose.z))
        e_x = actual_distance - target_z  # e_x > 0表示太远，需要向左移动；e_x < 0表示太近，需要向右移动

        # 前后误差：控制机器人相对tag的前后位置
        # pose.x > 0表示相机在tag右侧，机器人需要向前移动
        # pose.x < 0表示相机在tag左侧，机器人需要向后移动  
        e_y = float(pose.x) - float(target_x)  # e_y > 0表示需要向前，e_y < 0表示需要向后

        # 偏航：相对目标偏航角的误差
        raw_yaw = float(pose.yaw)
        e_yaw = AlignmentUtils.YAW_SIGN * (raw_yaw - target_yaw)

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
            return

        if ay > 0:
            # 纠正前后位置误差
            if e_y > 0:
                base_move('forward_slow')  # 需要向前
            else:
                base_move('backward_slow') # 需要向后
            return

        base_stop()


    @staticmethod
    def _rotate_discrete(e_yaw: float) -> None:
        """
        根据 e_yaw 误差发出一次“旋转”离散指令。
        只使用 slow 档。
        """
        ayaw = abs(e_yaw)
        if ayaw <= DEFAULT_TOLERANCE_YAW:
            return

        if e_yaw > 0:
            base_rotate('ccw_slow')
        else:
            base_rotate('cw_slow')
            
        # 离散控制模式：发出指令后立即停止
        base_stop()

    @staticmethod
    def execute_alignment_move(e_x: float, e_y: float, e_yaw: float, rotation_threshold: float = 0.05):
        """
        执行对齐移动：优先处理旋转（若超阈值），否则处理平移。
        """
        if abs(e_yaw) > rotation_threshold:
            AlignmentUtils._rotate_discrete(e_yaw)
        else:
            AlignmentUtils._move_discrete(e_x, e_y)

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
            time.sleep(0.05)

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
                time.sleep(0.05)
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
            time.sleep(0.05)

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
