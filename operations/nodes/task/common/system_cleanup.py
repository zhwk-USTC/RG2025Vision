from core.logger import logger
from vision import get_vision
from communicate import stop_serial
from operations.utils.communicate_utils import base_stop
from operations.debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory
import time

class SystemCleanup:
    """
    系统清理任务
    - 停止运动和执行器
    - 关闭视觉系统
    - 关闭通讯连接
    """
    
    def __init__(self, 
                 stop_base: bool = True,
                 stop_vision: bool = False,  # 默认不关闭视觉系统
                 stop_communication: bool = True,
                 exit_delay: float = 1.0):
        """
        参数：
        - stop_base: 是否停止底盘运动
        - stop_vision: 是否关闭视觉系统
        - stop_communication: 是否关闭通讯连接
        - exit_delay: 清理完成后的等待时间
        """
        self.stop_base = stop_base
        self.stop_vision = stop_vision
        self.stop_communication = stop_communication
        self.exit_delay = exit_delay
        self._done = False

    def run(self) -> bool:
        if self._done:
            logger.info("[SystemCleanup] 清理已完成，跳过")
            return True

        logger.info("[SystemCleanup] 开始系统清理")
        ok = True

        # 1) 停止底盘和执行器
        if self.stop_base:
            try:
                base_stop()
                logger.info("[SystemCleanup] 底盘已停止")
                set_debug_var('cleanup_base_stop', True, 
                             DebugLevel.SUCCESS, DebugCategory.STATUS, "底盘已安全停止")
            except Exception as e:
                logger.warning(f"[SystemCleanup] 底盘停止异常：{e}")
                set_debug_var('cleanup_base_error', str(e), 
                             DebugLevel.ERROR, DebugCategory.ERROR, "底盘停止时发生错误")
                ok = False

        # 2) 关闭视觉系统（可选）
        if self.stop_vision:
            try:
                vs = get_vision()
                vs.shutdown()
                logger.info("[SystemCleanup] 视觉系统已关闭")
                set_debug_var('cleanup_vision_stop', True, 
                             DebugLevel.SUCCESS, DebugCategory.STATUS, "视觉系统已关闭")
            except Exception as e:
                logger.warning(f"[SystemCleanup] 视觉系统清理异常：{e}")
                set_debug_var('cleanup_vision_error', str(e), 
                             DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统关闭时发生错误")
                ok = False

        # 3) 关闭通讯连接
        if self.stop_communication:
            try:
                stop_serial()
                logger.info("[SystemCleanup] 通讯连接已关闭")
                set_debug_var('cleanup_communication_stop', True, 
                             DebugLevel.SUCCESS, DebugCategory.STATUS, "通讯连接已关闭")
            except Exception as e:
                logger.warning(f"[SystemCleanup] 通讯关闭异常：{e}")
                set_debug_var('cleanup_communication_error', str(e), 
                             DebugLevel.ERROR, DebugCategory.ERROR, "通讯关闭时发生错误")
                ok = False

        self._done = True
        
        set_debug_var('cleanup_done', True, 
                     DebugLevel.SUCCESS, DebugCategory.STATUS, "系统清理任务已完成")
        logger.info(f"[SystemCleanup] 系统清理完成，{self.exit_delay}秒后继续")
        
        if self.exit_delay > 0:
            time.sleep(self.exit_delay)
        
        return ok