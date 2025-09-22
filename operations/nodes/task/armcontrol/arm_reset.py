from core.logger import logger
from ....utils.communicate_utils import arm_reset
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmReset:
    """
    机械臂复位任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmReset] 执行机械臂复位")

        try:
            set_debug_var('arm_action', 'reset',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂复位动作")

            arm_reset()
            logger.info("[ArmReset] 机械臂复位完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂复位成功")

        except Exception as e:
            logger.error(f"[ArmReset] 机械臂复位异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂复位时发生错误")
            return False

        return True