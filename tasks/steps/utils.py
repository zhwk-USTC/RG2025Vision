"""
步骤工具函数模块
包含各个步骤中经常复用的代码，如位姿定位、对齐控制等
"""

from typing import Optional, Dict, Any, Tuple, Union, Literal
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
from ..debug_vars_enhanced import set_debug_var, set_debug_image, DebugLevel, DebugCategory
import time

# 定义相机键名类型
CameraKey = Union[Literal['front'], Literal['left'], Literal['gripper']]


class VisionUtils:
    """视觉相关工具函数"""
    
    @staticmethod
    def check_vision_system(error_prefix: str = "vision_error") -> bool:
        """
        检查视觉系统是否准备就绪
        
        Args:
            error_prefix: 错误调试变量前缀
            
        Returns:
            bool: 视觉系统是否准备就绪
        """
        vs = get_vision()
        if not vs:
            set_debug_var(error_prefix, 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return False
        return True
    
    @staticmethod
    def get_frame_safely(cam_key: CameraKey, error_prefix: str = "frame_error", debug_image_key: Optional[str] = None, debug_description: str = ""):
        """
        安全地获取相机帧
        
        Args:
            cam_key: 相机键名
            error_prefix: 错误调试变量前缀
            debug_image_key: 调试图像键名
            debug_description: 调试图像描述
            
        Returns:
            frame: 图像帧，如果失败返回None
        """
        vs = get_vision()
        if not vs:
            return None
            
        frame = vs.read_frame(cam_key)  # type: ignore
        if frame is None:
            set_debug_var(error_prefix, 'empty frame', DebugLevel.ERROR, DebugCategory.ERROR, "无法获取相机帧")
            return None
            
        # 如果指定了调试图像键名，则保存调试图像
        if debug_image_key:
            set_debug_image(debug_image_key, frame, debug_description)
            
        return frame
    
    @staticmethod
    def detect_apriltag_with_retry(cam_key: CameraKey, target_tag_id: Optional[int] = None, 
                                 max_retries: int = 20, retry_delay: float = 0.05,
                                 debug_prefix: str = "tag", debug_description: str = "标签检测"):
        """
        带重试的AprilTag检测
        
        Args:
            cam_key: 相机键名
            target_tag_id: 目标标签ID，None表示使用第一个检测到的标签
            max_retries: 最大重试次数
            retry_delay: 重试间隔时间
            debug_prefix: 调试变量前缀
            debug_description: 调试描述
            
        Returns:
            tuple: (detection, pose) 或 (None, None) 如果失败
        """
        vs = get_vision()
        if not vs:
            set_debug_var(f'{debug_prefix}_error', 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return None, None
        
        iter_cnt = 0
        while iter_cnt <= max_retries:
            # 获取帧
            frame = VisionUtils.get_frame_safely(
                cam_key, 
                f'{debug_prefix}_error', 
                f'{debug_prefix}_frame', 
                f"{debug_description}时的相机帧"
            )
            if frame is None:
                return None, None
            
            # 检测AprilTag
            intr = vs.get_camera_intrinsics(cam_key)  # type: ignore
            dets = vs.detect_tag36h11(frame, intr)
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
            det = dets[0] if target_tag_id is None else next(
                (d for d in dets if d.tag_id == target_tag_id), dets[0])
            set_debug_var(f'{debug_prefix}_tag_id', getattr(det, 'tag_id', None), 
                         DebugLevel.INFO, DebugCategory.DETECTION, f"当前检测到的{debug_description}ID")
            
            # 获取位姿
            pose = vs.locate_from_tag(det)
            if pose is None:
                logger.error(f"[{debug_description}] 无法从标签中定位")
                set_debug_var(f'{debug_prefix}_error', 'pose none', 
                             DebugLevel.ERROR, DebugCategory.POSITION, "无法从标签获取位姿信息")
                return None, None
            
            return det, pose
        
        return None, None


class AlignmentUtils:
    """对齐控制相关工具函数"""
    
    @staticmethod
    def calculate_position_error(pose, target_distance: float) -> Tuple[float, float, float]:
        """
        计算位置误差
        
        Args:
            pose: 位姿对象
            target_distance: 目标距离
            
        Returns:
            tuple: (e_x, e_y, e_yaw) 位置误差
        """
        e_x = pose.x - target_distance
        e_y = pose.y
        e_yaw = pose.yaw
        return e_x, e_y, e_yaw
    
    @staticmethod
    def is_aligned(e_x: float, e_y: float, e_yaw: float, 
                   tolerance_xy: float = 0.05, tolerance_yaw: float = 0.1) -> bool:
        """
        判断是否已对齐
        
        Args:
            e_x, e_y, e_yaw: 位置误差
            tolerance_xy: xy方向容差
            tolerance_yaw: 角度容差
            
        Returns:
            bool: 是否已对齐
        """
        return abs(e_x) < tolerance_xy and abs(e_y) < tolerance_xy and abs(e_yaw) < tolerance_yaw
    
    @staticmethod
    def execute_alignment_move(e_x: float, e_y: float, e_yaw: float, 
                              rotation_threshold: float = 0.05):
        """
        执行对齐移动
        
        Args:
            e_x, e_y, e_yaw: 位置误差
            rotation_threshold: 旋转阈值，超过此值才执行旋转
        """
        base_move(e_x, -e_y)
        if abs(e_yaw) > rotation_threshold:
            base_rotate(-e_yaw)
    
    @staticmethod
    def apriltag_alignment_loop(cam_key: CameraKey, target_tag_id: Optional[int], 
                               target_distance: float, debug_prefix: str, 
                               task_name: str, max_retries: int = 20) -> bool:
        """
        AprilTag对齐控制循环
        
        Args:
            cam_key: 相机键名
            target_tag_id: 目标标签ID
            target_distance: 目标距离
            debug_prefix: 调试变量前缀
            task_name: 任务名称（用于日志）
            max_retries: 最大重试次数
            
        Returns:
            bool: 对齐是否成功
        """
        # 检查视觉系统
        if not VisionUtils.check_vision_system(f'{debug_prefix}_error'):
            return False
        
        while True:
            # 检测标签并获取位姿
            det, pose = VisionUtils.detect_apriltag_with_retry(
                cam_key, target_tag_id, max_retries, 0.05, debug_prefix, task_name
            )
            
            if pose is None:
                return False
            
            # 计算误差
            e_x, e_y, e_yaw = AlignmentUtils.calculate_position_error(pose, target_distance)
            set_debug_var(f'{debug_prefix}_err', 
                         {'ex': round(e_x,3), 'ey': round(e_y,3), 'eyaw': round(e_yaw,3)}, 
                         DebugLevel.INFO, DebugCategory.POSITION, "与目标位置的误差")
            
            # 判断是否到达目标位置
            if AlignmentUtils.is_aligned(e_x, e_y, e_yaw):
                logger.info(f"[{task_name}] 已对齐到目标位置")
                set_debug_var(f'{debug_prefix}_status', 'done', 
                             DebugLevel.SUCCESS, DebugCategory.STATUS, f"已成功对齐到{task_name}")
                break
            
            # 执行移动
            AlignmentUtils.execute_alignment_move(e_x, e_y, e_yaw)
            set_debug_var(f'{debug_prefix}_status', 'adjusting', 
                         DebugLevel.INFO, DebugCategory.STATUS, f"正在调整位置对齐{task_name}")
            time.sleep(0.05)
        
        return True


class CustomDetectionUtils:
    """自定义检测相关工具函数"""
    
    @staticmethod
    def detect_with_retry(detection_func, frame_getter, error_handler,
                         max_retries: int = 20, retry_delay: float = 0.05,
                         debug_prefix: str = "detection") -> Any:
        """
        通用的带重试的检测函数
        
        Args:
            detection_func: 检测函数，接受frame参数
            frame_getter: 帧获取函数
            error_handler: 错误处理函数
            max_retries: 最大重试次数
            retry_delay: 重试间隔
            debug_prefix: 调试前缀
            
        Returns:
            检测结果，失败返回None
        """
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
    def custom_detection_alignment_loop(cam_key: CameraKey, detection_func, target_distance: float,
                                      debug_prefix: str, task_name: str, max_retries: int = 20) -> bool:
        """
        自定义检测的对齐控制循环
        
        Args:
            cam_key: 相机键名
            detection_func: 检测函数，接受frame参数，返回包含x,y,yaw的字典或None
            target_distance: 目标距离  
            debug_prefix: 调试变量前缀
            task_name: 任务名称
            max_retries: 最大重试次数
            
        Returns:
            bool: 对齐是否成功
        """
        # 检查视觉系统
        if not VisionUtils.check_vision_system(f'{debug_prefix}_error'):
            return False
        
        iter_cnt = 0
        while True:
            # 获取帧
            frame = VisionUtils.get_frame_safely(
                cam_key, f'{debug_prefix}_error', f'{debug_prefix}_frame', f"{task_name}时的相机帧"
            )
            if frame is None:
                return False
            
            # 执行检测
            detection_result = detection_func(frame)
            if detection_result is None:
                if iter_cnt >= max_retries:
                    logger.error(f"[{task_name}] 未检测到目标")
                    set_debug_var(f'{debug_prefix}_error', 'no target found', 
                                DebugLevel.ERROR, DebugCategory.DETECTION, f"未检测到{task_name}目标")
                    return False
                iter_cnt += 1
                time.sleep(0.05)
                continue
            
            set_debug_var(f'{debug_prefix}_target_pos', detection_result, 
                         DebugLevel.INFO, DebugCategory.DETECTION, "检测到的目标位置")
            
            # 计算误差
            e_x = detection_result.get('x', 0) - target_distance
            e_y = detection_result.get('y', 0)
            e_yaw = detection_result.get('yaw', 0)
            
            set_debug_var(f'{debug_prefix}_err', {
                'ex': round(e_x, 3), 
                'ey': round(e_y, 3), 
                'eyaw': round(e_yaw, 3)
            }, DebugLevel.INFO, DebugCategory.POSITION, "与目标位置的误差")
            
            # 判断是否已经对齐
            if AlignmentUtils.is_aligned(e_x, e_y, e_yaw):
                logger.info(f"[{task_name}] 已对齐到目标")
                set_debug_var(f'{debug_prefix}_status', 'aligned', 
                             DebugLevel.SUCCESS, DebugCategory.STATUS, f"已成功对齐到{task_name}")
                break
            
            # 执行移动调整
            AlignmentUtils.execute_alignment_move(e_x, e_y, e_yaw)
            set_debug_var(f'{debug_prefix}_status', 'adjusting', 
                         DebugLevel.INFO, DebugCategory.STATUS, f"正在调整{task_name}位置")
            time.sleep(0.05)
        
        return True


# 便捷函数，为了向后兼容和简化使用
def align_to_apriltag(cam_key: CameraKey, target_tag_id: Optional[int], target_distance: float,
                     debug_prefix: str, task_name: str) -> bool:
    """
    便捷的AprilTag对齐函数
    
    Args:
        cam_key: 相机键名  
        target_tag_id: 目标标签ID
        target_distance: 目标距离
        debug_prefix: 调试变量前缀
        task_name: 任务名称
        
    Returns:
        bool: 对齐是否成功
    """
    return AlignmentUtils.apriltag_alignment_loop(
        cam_key, target_tag_id, target_distance, debug_prefix, task_name
    )

def align_to_custom_target(cam_key: CameraKey, detection_func, target_distance: float,
                          debug_prefix: str, task_name: str) -> bool:
    """
    便捷的自定义目标对齐函数
    
    Args:
        cam_key: 相机键名
        detection_func: 检测函数，接受frame参数，返回包含x,y,yaw的字典或None
        target_distance: 目标距离
        debug_prefix: 调试变量前缀
        task_name: 任务名称
        
    Returns:
        bool: 对齐是否成功
    """
    return CustomDetectionUtils.custom_detection_alignment_loop(
        cam_key, detection_func, target_distance, debug_prefix, task_name
    )
