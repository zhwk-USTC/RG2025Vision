from typing import Optional
from ...utils.communicate_utils import set_fire_speed, fire_once
from ...debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory
from core.logger import logger

class FireControl:
    """
    通用发射控制任务
    支持设置发射速度和发射
    """

    def __init__(self, fire_speed: Optional[float] = None, fire_count: int = 1):
        """
        参数：
        - fire_speed: 发射速度（如果为None则不设置速度）
        - fire_count: 发射次数
        """
        self.fire_speed = fire_speed
        self.fire_count = fire_count

    def run(self) -> bool:
        logger.info(f"[FireControl] 开始发射控制，发射{self.fire_count}次")
        
        try:
            # 设置发射速度（如果指定）
            if self.fire_speed is not None:
                set_fire_speed(self.fire_speed)
                set_debug_var('fire_speed_set', self.fire_speed, 
                             DebugLevel.INFO, DebugCategory.CONTROL, "发射速度已设置")
                logger.info(f"[FireControl] 发射速度设置为: {self.fire_speed}")
            
            # 执行发射
            for i in range(self.fire_count):
                fire_once()
                logger.info(f"[FireControl] 第{i+1}次发射完成")
                set_debug_var(f'fire_{i+1}_done', True, 
                             DebugLevel.SUCCESS, DebugCategory.STATUS, f"第{i+1}次发射完成")
            
            set_debug_var('fire_control_status', 'success', 
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "发射控制成功完成")
            logger.info("[FireControl] 发射控制完成")
            
        except Exception as e:
            logger.error(f"[FireControl] 发射控制异常：{e}")
            set_debug_var('fire_control_error', str(e), 
                         DebugLevel.ERROR, DebugCategory.ERROR, "发射控制时发生错误")
            return False
        
        return True