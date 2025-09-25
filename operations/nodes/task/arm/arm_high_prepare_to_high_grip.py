from core.logger import logger
from ....utils.communicate_utils import arm_high_prepare_to_high_grip
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmHighPrepareToHighGrip:
    """
    机械臂高位准备到高位夹取任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmHighPrepareToHighGrip] 执行机械臂高位准备到高位夹取")

        try:
            set_debug_var('arm_action', 'high_prepare_to_high_grip',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂高位准备到高位夹取动作")

            arm_high_prepare_to_high_grip()
            logger.info("[ArmHighPrepareToHighGrip] 机械臂高位准备到高位夹取完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂高位准备到高位夹取成功")

        except Exception as e:
            logger.error(f"[ArmHighPrepareToHighGrip] 机械臂高位准备到高位夹取异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂高位准备到高位夹取时发生错误")
            return False

        return True