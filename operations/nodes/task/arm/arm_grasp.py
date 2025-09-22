from core.logger import logger
from ....utils.communicate_utils import arm_grasp_dart
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmGrasp:
    """
    机械臂抓取任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmGrasp] 执行机械臂抓取")

        try:
            set_debug_var('arm_action', 'grasp',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂抓取动作")

            arm_grasp_dart()
            logger.info("[ArmGrasp] 机械臂抓取完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂抓取成功")

        except Exception as e:
            logger.error(f"[ArmGrasp] 机械臂抓取异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂抓取时发生错误")
            return False

        return True