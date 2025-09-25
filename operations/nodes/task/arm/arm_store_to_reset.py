from core.logger import logger
from ....utils.communicate_utils import arm_store_to_reset
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmStoreToReset:
    """
    机械臂存储到复位任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmStoreToReset] 执行机械臂存储到复位")

        try:
            set_debug_var('arm_action', 'store_to_reset',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂存储到复位动作")

            arm_store_to_reset()
            logger.info("[ArmStoreToReset] 机械臂存储到复位完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂存储到复位成功")

        except Exception as e:
            logger.error(f"[ArmStoreToReset] 机械臂存储到复位异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂存储到复位时发生错误")
            return False

        return True