import time
from core.logger import logger
from ....utils.communicate_utils import base_set_move, base_stop, base_set_rotate
from ....utils.base_movement_utils import MovementUtils
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class BaseMove:
    """
    通用底盘移动任务
    支持多种移动模式：前后左右移动，定时移动
    """

    def __init__(
        self,
        direction: str = 'forward',
        speed: str = 'slow',
        duration: float = 1.0,
    ) -> None:
        """
        参数：
        - direction: 移动方向 ('forward', 'backward', 'left', 'right')
        - speed: 移动速度 ('slow', 'fast')
        - duration: 移动持续时间（秒）
        """
        self.direction = direction
        self.speed = speed
        self.duration = duration

    def run(self) -> bool:
        logger.info(f"[BaseMove] 开始移动: {self.direction}_{self.speed}, 持续{self.duration}秒")
        
        try:
            set_debug_var('base_move_direction', f"{self.direction}_{self.speed}", 
                         DebugLevel.INFO, DebugCategory.CONTROL, "底盘移动方向和速度")
            set_debug_var('base_move_duration', self.duration, 
                         DebugLevel.INFO, DebugCategory.CONTROL, "底盘移动持续时间")
            
            # 执行移动
            move_command = f"{self.direction}_{self.speed}"
            MovementUtils.execute_move(move_command, self.duration)  # type: ignore
            
            logger.info("[BaseMove] 移动完成")
            set_debug_var('base_move_status', 'success', 
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "底盘移动成功")
            
        except Exception as e:
            logger.error(f"[BaseMove] 移动异常：{e}")
            set_debug_var('base_move_error', str(e), 
                         DebugLevel.ERROR, DebugCategory.ERROR, "底盘移动时发生错误")
            base_stop()
            return False
        
        return True