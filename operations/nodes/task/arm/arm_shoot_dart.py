from core.logger import logger
from ....utils.communicate_utils import (
    arm_reset_gripping_to_shot,
    arm_shot_to_reset
)
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmShootDart:
    """
    复合task：射击飞镖并返回复位
    抓取复位 -> 射击 -> 复位
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmShootDart] 开始执行射击飞镖并返回复位")

        try:
            set_debug_var('arm_composite_action', 'shoot_dart',
                         DebugLevel.INFO, DebugCategory.CONTROL, "复合动作：射击飞镖")

            # 步骤1: 抓取复位 -> 射击
            logger.info("[ArmShootDart] 步骤1: 抓取复位 -> 射击")
            arm_reset_gripping_to_shot()

            # 步骤2: 射击 -> 复位
            logger.info("[ArmShootDart] 步骤2: 射击 -> 复位")
            arm_shot_to_reset()

            logger.info("[ArmShootDart] 射击飞镖并返回复位完成")
            set_debug_var('arm_composite_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "射击飞镖动作成功")

            return True

        except Exception as e:
            logger.error(f"[ArmShootDart] 射击飞镖异常：{e}")
            set_debug_var('arm_composite_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "射击飞镖动作失败")
            return False