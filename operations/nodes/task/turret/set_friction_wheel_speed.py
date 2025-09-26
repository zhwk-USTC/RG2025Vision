from core.logger import logger
from ....utils.communicate_utils import set_friction_wheel_speed
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class SetFrictionWheelSpeed:
    """
    设置摩擦轮速度
    """

    def __init__(self, speed: float = 0.0):
        self.speed = speed

    def run(self) -> bool:
        logger.info(f"[SetFrictionWheelSpeed] 开始设置摩擦轮速度: {self.speed}")

        try:
            set_debug_var('friction_wheel_action', 'set_speed',
                         DebugLevel.INFO, DebugCategory.CONTROL, f"设置摩擦轮速度: {self.speed}")

            set_friction_wheel_speed(self.speed)

            logger.info(f"[SetFrictionWheelSpeed] 设置摩擦轮速度完成: {self.speed}")
            set_debug_var('friction_wheel_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, f"设置摩擦轮速度成功: {self.speed}")

            return True

        except Exception as e:
            logger.error(f"[SetFrictionWheelSpeed] 设置摩擦轮速度异常：{e}")
            set_debug_var('friction_wheel_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "设置摩擦轮速度失败")
            return False