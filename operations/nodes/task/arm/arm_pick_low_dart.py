from core.logger import logger
from ....utils.communicate_utils import (
    arm_reset_to_low_prepare,
    arm_low_prepare_to_low_grip,
    arm_low_grip_to_reset_gripping
)
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmPickLowDart:
    """
    复合task：完整的低位取镖动作
    复位 -> 低位准备 -> 低位夹取 -> 抓取复位
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmPickLowDart] 开始执行完整的低位取镖动作")

        try:
            set_debug_var('arm_composite_action', 'pick_low_dart',
                         DebugLevel.INFO, DebugCategory.CONTROL, "复合动作：低位取镖")

            # 步骤1: 复位 -> 低位准备
            logger.info("[ArmPickLowDart] 步骤1: 复位 -> 低位准备")
            arm_reset_to_low_prepare()

            # 步骤2: 低位准备 -> 低位夹取
            logger.info("[ArmPickLowDart] 步骤2: 低位准备 -> 低位夹取")
            arm_low_prepare_to_low_grip()

            # 步骤3: 低位夹取 -> 抓取复位
            logger.info("[ArmPickLowDart] 步骤3: 低位夹取 -> 抓取复位")
            arm_low_grip_to_reset_gripping()

            logger.info("[ArmPickLowDart] 完整的低位取镖动作执行完成")
            set_debug_var('arm_composite_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "低位取镖动作成功")

            return True

        except Exception as e:
            logger.error(f"[ArmPickLowDart] 低位取镖动作异常：{e}")
            set_debug_var('arm_composite_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "低位取镖动作失败")
            return False