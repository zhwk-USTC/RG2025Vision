from core.logger import logger
from ....utils.communicate_utils import arm_low_prepare_to_low_grip
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmLowPrepareToLowGrip:
    """
    机械臂低位准备到低位夹取任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmLowPrepareToLowGrip] 执行机械臂低位准备到低位夹取")

        try:
            set_debug_var('arm_action', 'low_prepare_to_low_grip',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂低位准备到低位夹取动作")

            arm_low_prepare_to_low_grip()
            logger.info("[ArmLowPrepareToLowGrip] 机械臂低位准备到低位夹取完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂低位准备到低位夹取成功")

        except Exception as e:
            logger.error(f"[ArmLowPrepareToLowGrip] 机械臂低位准备到低位夹取异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂低位准备到低位夹取时发生错误")
            return False

        return True