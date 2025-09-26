from core.logger import logger
from ....utils.communicate_utils import friction_wheel_stop
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class FrictionWheelStop:
    """
    停止摩擦轮
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[FrictionWheelStop] 开始停止摩擦轮")

        try:
            set_debug_var('friction_wheel_action', 'stop',
                         DebugLevel.INFO, DebugCategory.CONTROL, "停止摩擦轮")

            friction_wheel_stop()

            logger.info("[FrictionWheelStop] 停止摩擦轮完成")
            set_debug_var('friction_wheel_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "停止摩擦轮成功")

            return True

        except Exception as e:
            logger.error(f"[FrictionWheelStop] 停止摩擦轮异常：{e}")
            set_debug_var('friction_wheel_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "停止摩擦轮失败")
            return False