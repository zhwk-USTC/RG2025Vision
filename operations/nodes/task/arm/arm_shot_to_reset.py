from core.logger import logger
from ....utils.communicate_utils import arm_shot_to_reset
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmShotToReset:
    """
    机械臂射击到复位任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmShotToReset] 执行机械臂射击到复位")

        try:
            set_debug_var('arm_action', 'shot_to_reset',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂射击到复位动作")

            arm_shot_to_reset()
            logger.info("[ArmShotToReset] 机械臂射击到复位完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂射击到复位成功")

        except Exception as e:
            logger.error(f"[ArmShotToReset] 机械臂射击到复位异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂射击到复位时发生错误")
            return False

        return True