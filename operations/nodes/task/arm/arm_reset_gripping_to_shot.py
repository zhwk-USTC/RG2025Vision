from core.logger import logger
from ....utils.communicate_utils import arm_reset_gripping_to_shot
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmResetGrippingToShot:
    """
    机械臂抓取复位到射击任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmResetGrippingToShot] 执行机械臂抓取复位到射击")

        try:
            set_debug_var('arm_action', 'reset_gripping_to_shot',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂抓取复位到射击动作")

            arm_reset_gripping_to_shot()
            logger.info("[ArmResetGrippingToShot] 机械臂抓取复位到射击完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂抓取复位到射击成功")

        except Exception as e:
            logger.error(f"[ArmResetGrippingToShot] 机械臂抓取复位到射击异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂抓取复位到射击时发生错误")
            return False

        return True