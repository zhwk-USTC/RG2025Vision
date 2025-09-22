from core.logger import logger
from ....utils.communicate_utils import base_stop
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class BaseStop:
    """
    底盘停止任务
    立即停止底盘的所有运动
    """

    def __init__(self) -> None:
        """
        无需参数，立即停止底盘
        """
        pass

    def run(self) -> bool:
        logger.info("[BaseStop] 执行底盘停止")
        
        try:
            set_debug_var('base_stop_command', 'executing', 
                         DebugLevel.INFO, DebugCategory.CONTROL, "底盘停止指令执行中")
            
            # 执行停止
            base_stop()
            
            logger.info("[BaseStop] 底盘已停止")
            set_debug_var('base_stop_status', 'success', 
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "底盘停止成功")
            
        except Exception as e:
            logger.error(f"[BaseStop] 停止异常：{e}")
            set_debug_var('base_stop_error', str(e), 
                         DebugLevel.ERROR, DebugCategory.ERROR, "底盘停止时发生错误")
            return False
        
        return True