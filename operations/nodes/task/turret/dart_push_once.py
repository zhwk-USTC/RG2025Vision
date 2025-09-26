from core.logger import logger
from ....utils.communicate_utils import dart_push_once as communicate_dart_push_once
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class DartPushOnce:
    """
    推进飞镖向前，然后回到原位
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[DartPushOnce] 开始执行推进飞镖")

        try:
            set_debug_var('dart_push_action', 'push_once',
                         DebugLevel.INFO, DebugCategory.CONTROL, "推进飞镖向前")

            communicate_dart_push_once()

            logger.info("[DartPushOnce] 推进飞镖完成")
            set_debug_var('dart_push_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "推进飞镖成功")

            return True

        except Exception as e:
            logger.error(f"[DartPushOnce] 推进飞镖异常：{e}")
            set_debug_var('dart_push_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "推进飞镖失败")
            return False