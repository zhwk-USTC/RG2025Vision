from core.logger import logger
from ....utils.communicate_utils import arm_low_grip_to_reset_gripping
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmLowGripToResetGripping:
    """
    机械臂低位夹取到抓取复位任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmLowGripToResetGripping] 执行机械臂低位夹取到抓取复位")

        try:
            set_debug_var('arm_action', 'low_grip_to_reset_gripping',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂低位夹取到抓取复位动作")

            arm_low_grip_to_reset_gripping()
            logger.info("[ArmLowGripToResetGripping] 机械臂低位夹取到抓取复位完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂低位夹取到抓取复位成功")

        except Exception as e:
            logger.error(f"[ArmLowGripToResetGripping] 机械臂低位夹取到抓取复位异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂低位夹取到抓取复位时发生错误")
            return False

        return True