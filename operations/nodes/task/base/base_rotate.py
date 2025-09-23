import time
from core.logger import logger
from ....utils.communicate_utils import base_set_rotate, base_stop
from ....utils.base_movement_utils import MovementUtils
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class BaseRotate:
    """
    通用底盘旋转任务
    支持顺时针和逆时针旋转，可控制速度和持续时间
    """

    def __init__(
        self,
        direction: str = 'cw',
        speed: str = 'slow',
        duration: float = 1.0,
    ) -> None:
        """
        参数：
        - direction: 旋转方向 ('cw' 顺时针, 'ccw' 逆时针)
        - speed: 旋转速度 ('slow', 'fast')
        - duration: 旋转持续时间（秒）
        """
        self.direction = direction
        self.speed = speed
        self.duration = duration

    def run(self) -> bool:
        logger.info(f"[BaseRotate] 开始旋转: {self.direction}_{self.speed}, 持续{self.duration}秒")
        
        try:
            set_debug_var('base_rotate_direction', f"{self.direction}_{self.speed}", 
                         DebugLevel.INFO, DebugCategory.CONTROL, "底盘旋转方向和速度")
            set_debug_var('base_rotate_duration', self.duration, 
                         DebugLevel.INFO, DebugCategory.CONTROL, "底盘旋转持续时间")
            
            # 执行旋转（使用平滑旋转）
            rotate_command = f"{self.direction}_{self.speed}"
            MovementUtils.execute_smooth_rotate(rotate_command, self.duration)  # type: ignore
            
            logger.info("[BaseRotate] 旋转完成")
            set_debug_var('base_rotate_status', 'success', 
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "底盘旋转成功")
            
        except Exception as e:
            logger.error(f"[BaseRotate] 旋转异常：{e}")
            set_debug_var('base_rotate_error', str(e), 
                         DebugLevel.ERROR, DebugCategory.ERROR, "底盘旋转时发生错误")
            base_stop()
            return False
        
        return True