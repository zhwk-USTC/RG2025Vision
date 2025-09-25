from core.logger import logger
from ....utils.communicate_utils import arm_reset_to_low_prepare
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmResetToLowPrepare:
    """
    机械臂复位到低位准备任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmResetToLowPrepare] 执行机械臂复位到低位准备")

        try:
            set_debug_var('arm_action', 'reset_to_low_prepare',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂复位到低位准备动作")

            arm_reset_to_low_prepare()
            logger.info("[ArmResetToLowPrepare] 机械臂复位到低位准备完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂复位到低位准备成功")

        except Exception as e:
            logger.error(f"[ArmResetToLowPrepare] 机械臂复位到低位准备异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂复位到低位准备时发生错误")
            return False

        return True