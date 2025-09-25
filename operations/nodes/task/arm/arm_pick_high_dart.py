from core.logger import logger
from ....utils.communicate_utils import (
    arm_reset_to_high_prepare,
    arm_high_prepare_to_high_grip,
    arm_high_grip_to_reset_gripping
)
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmPickHighDart:
    """
    复合task：完整的高位取镖动作
    复位 -> 高位准备 -> 高位夹取 -> 抓取复位
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmPickHighDart] 开始执行完整的高位取镖动作")

        try:
            set_debug_var('arm_composite_action', 'pick_high_dart',
                         DebugLevel.INFO, DebugCategory.CONTROL, "复合动作：高位取镖")

            # 步骤1: 复位 -> 高位准备
            logger.info("[ArmPickHighDart] 步骤1: 复位 -> 高位准备")
            arm_reset_to_high_prepare()

            # 步骤2: 高位准备 -> 高位夹取
            logger.info("[ArmPickHighDart] 步骤2: 高位准备 -> 高位夹取")
            arm_high_prepare_to_high_grip()

            # 步骤3: 高位夹取 -> 抓取复位
            logger.info("[ArmPickHighDart] 步骤3: 高位夹取 -> 抓取复位")
            arm_high_grip_to_reset_gripping()

            logger.info("[ArmPickHighDart] 完整的高位取镖动作执行完成")
            set_debug_var('arm_composite_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "高位取镖动作成功")

            return True

        except Exception as e:
            logger.error(f"[ArmPickHighDart] 高位取镖动作异常：{e}")
            set_debug_var('arm_composite_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "高位取镖动作失败")
            return False