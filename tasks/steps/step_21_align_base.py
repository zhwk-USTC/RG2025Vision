from typing import Optional, cast
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
from ..debug_vars_enhanced import set_debug_var, set_debug_image, DebugLevel, DebugCategory
from .utils import align_to_custom_target, CameraKey
import time

class Step21AlignBase:
    """
    底盘对齐到最左边的飞镖
    """
    def __init__(self, cam_key: str = "left", keep_dist: float = 0.5):
        self.cam_key = cam_key
        self.keep_dist = keep_dist

    def run(self) -> bool:
        # 使用utils中的自定义目标对齐函数
        return align_to_custom_target(
            cam_key=cast(CameraKey, self.cam_key),
            detection_func=self._detect_leftmost_dart,
            target_distance=self.keep_dist,
            debug_prefix="align_base",
            task_name="底盘对齐到飞镖"
        )
    
    def _detect_leftmost_dart(self, frame) -> Optional[dict]:
        """
        检测最左边的飞镖
        TODO: 实现具体的飞镖检测算法
        
        Args:
            frame: 输入图像帧
            
        Returns:
            dict: 飞镖位置信息 {'x': float, 'y': float, 'z': float, 'yaw': float}
            None: 未检测到飞镖
        """
        # TODO: 在这里实现飞镖检测算法
        # 1. 图像预处理
        # 2. 飞镖特征检测/识别
        # 3. 找到最左边的飞镖
        # 4. 计算相对位置
        
        # 临时返回伪造数据用于测试
        dart_pos = {'x': 0.1, 'y': 0.2, 'z': 0.0, 'yaw': 0.0}
        set_debug_var('detect_leftmost_dart', dart_pos, DebugLevel.INFO, DebugCategory.DETECTION, "检测到的最左边飞镖位置")
        return dart_pos
