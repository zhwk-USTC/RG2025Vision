from typing import Optional
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
from ..debug_vars_enhanced import set_debug_var, set_debug_image, DebugLevel, DebugCategory
import time

class Step21AlignBase:
    """
    底盘对齐到最左边的飞镖
    """
    def __init__(self, cam_key: str = "left", keep_dist: float = 0.5):
        self.cam_key = cam_key
        self.keep_dist = keep_dist

    def run(self) -> bool:
        vs = get_vision()
        if not vs:
            set_debug_var('align_base_error', 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return False
        
        iter_cnt = 0
        while True:
            frame = vs.read_frame(self.cam_key)  # type: ignore
            if frame is None:
                set_debug_var('align_base_error', 'empty frame', DebugLevel.ERROR, DebugCategory.ERROR, "无法获取相机帧")
                return False
            
            # 存储当前原始帧（压缩后）
            set_debug_image('align_base_frame', frame, "底盘对齐时的相机帧")
            
            # 检测最左边的飞镖
            dart_pos = self._detect_leftmost_dart(frame)
            if dart_pos is None:
                if iter_cnt > 20:
                    logger.error("[AlignBase] 未检测到飞镖")
                    set_debug_var('align_base_error', 'no dart found', DebugLevel.ERROR, DebugCategory.DETECTION, "未检测到飞镖目标")
                    return False
                iter_cnt += 1
                time.sleep(0.05)
                continue
            
            set_debug_var('align_base_dart_pos', dart_pos, DebugLevel.INFO, DebugCategory.DETECTION, "检测到的飞镖位置")
            
            # 计算误差（假设dart_pos包含相对位置）
            e_x = dart_pos.get('x', 0) - self.keep_dist
            e_y = dart_pos.get('y', 0)
            e_yaw = dart_pos.get('yaw', 0)  # 如果有角度信息
            
            set_debug_var('align_base_err', {
                'ex': round(e_x, 3), 
                'ey': round(e_y, 3), 
                'eyaw': round(e_yaw, 3)
            }, DebugLevel.INFO, DebugCategory.POSITION, "与目标飞镖的位置误差")
            
            # 判断是否已经对齐
            if abs(e_x) < 0.05 and abs(e_y) < 0.05 and abs(e_yaw) < 0.1:
                logger.info("[AlignBase] 已对齐到最左边的飞镖")
                set_debug_var('align_base_status', 'aligned', DebugLevel.SUCCESS, DebugCategory.STATUS, "底盘已成功对齐到目标飞镖")
                break
            
            # 执行移动调整
            base_move(e_x, -e_y)
            if abs(e_yaw) > 0.05:  # 只有角度误差较大时才旋转
                base_rotate(-e_yaw)
            
            set_debug_var('align_base_status', 'adjusting', DebugLevel.INFO, DebugCategory.STATUS, "正在调整底盘位置")
            time.sleep(0.05)

        return True
    
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
