from core.logger import logger
from ....utils.communicate_utils import friction_wheel_start
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class FrictionWheelStart:
    """
    启动摩擦轮
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[FrictionWheelStart] 开始启动摩擦轮")

        try:
            set_debug_var('friction_wheel_action', 'start',
                         DebugLevel.INFO, DebugCategory.CONTROL, "启动摩擦轮")

            friction_wheel_start()

            logger.info("[FrictionWheelStart] 启动摩擦轮完成")
            set_debug_var('friction_wheel_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "启动摩擦轮成功")

            return True

        except Exception as e:
            logger.error(f"[FrictionWheelStart] 启动摩擦轮异常：{e}")
            set_debug_var('friction_wheel_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "启动摩擦轮失败")
            return False