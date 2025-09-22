from core.logger import logger
from ....utils.communicate_utils import arm_reset_to_prepare
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmPrepare:
    """
    机械臂准备位置任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmPrepare] 执行机械臂准备位置")

        try:
            set_debug_var('arm_action', 'prepare',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂准备位置动作")

            arm_reset_to_prepare()
            logger.info("[ArmPrepare] 机械臂准备位置完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂准备位置成功")

        except Exception as e:
            logger.error(f"[ArmPrepare] 机械臂准备位置异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂准备位置时发生错误")
            return False

        return True