from core.logger import logger
from ....utils.communicate_utils import arm_reset_to_store
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmResetToStore:
    """
    机械臂复位到存储任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmResetToStore] 执行机械臂复位到存储")

        try:
            set_debug_var('arm_action', 'reset_to_store',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂复位到存储动作")

            arm_reset_to_store()
            logger.info("[ArmResetToStore] 机械臂复位到存储完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂复位到存储成功")

        except Exception as e:
            logger.error(f"[ArmResetToStore] 机械臂复位到存储异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂复位到存储时发生错误")
            return False

        return True