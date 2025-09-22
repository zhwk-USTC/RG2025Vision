from core.logger import logger
from ....utils.communicate_utils import arm_reset, arm_reset_to_prepare, arm_grasp_dart, arm_load_dart
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmGraspAndLoad:
    """
    机械臂抓取和装载组合任务
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmGraspAndLoad] 执行机械臂抓取和装载")

        try:
            set_debug_var('arm_action', 'grasp_and_load',
                         DebugLevel.INFO, DebugCategory.CONTROL, "机械臂抓取和装载组合动作")

            # 复位
            arm_reset()
            logger.info("[ArmGraspAndLoad] 复位完成")

            # 准备位置
            arm_reset_to_prepare()
            logger.info("[ArmGraspAndLoad] 准备位置完成")

            # 抓取
            arm_grasp_dart()
            logger.info("[ArmGraspAndLoad] 抓取完成")

            # 装载
            arm_load_dart()
            logger.info("[ArmGraspAndLoad] 装载完成")

            set_debug_var('arm_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "机械臂抓取和装载成功")

        except Exception as e:
            logger.error(f"[ArmGraspAndLoad] 机械臂抓取和装载异常：{e}")
            set_debug_var('arm_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "机械臂抓取和装载时发生错误")
            return False

        return True