from core.logger import logger
from ....utils.communicate_utils import arm_load_dart
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmLoad:
    """
    机械臂装载任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmLoad] 执行机械臂装载")

        try:
            set_debug_var('arm_action', 'load',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂装载动作")

            arm_load_dart()
            logger.info("[ArmLoad] 机械臂装载完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂装载成功")

        except Exception as e:
            logger.error(f"[ArmLoad] 机械臂装载异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂装载时发生错误")
            return False

        return True