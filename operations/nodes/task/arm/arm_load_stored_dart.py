from core.logger import logger
from ....utils.communicate_utils import (
    arm_reset_to_store,
    arm_store_to_reset_gripping,
    arm_reset_gripping_to_shot,
    arm_shot_to_reset
)
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmLoadStoredDart:
    """
    复合task：从复位位置加载存储的飞镖到发射区并返回复位
    复位 -> 存储 -> 抓取复位 -> 射击位置 -> 复位
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmLoadStoredDart] 开始执行从复位位置加载存储的飞镖到发射区并返回复位")

        try:
            set_debug_var('arm_composite_action', 'load_stored_dart',
                         DebugLevel.INFO, DebugCategory.CONTROL, "复合动作：加载存储飞镖到发射区")

            # 步骤1: 复位 -> 存储
            logger.info("[ArmLoadStoredDart] 步骤1: 复位 -> 存储")
            arm_reset_to_store()

            # 步骤2: 存储 -> 抓取复位
            logger.info("[ArmLoadStoredDart] 步骤2: 存储 -> 抓取复位")
            arm_store_to_reset_gripping()

            # 步骤3: 抓取复位 -> 射击位置
            logger.info("[ArmLoadStoredDart] 步骤3: 抓取复位 -> 射击位置")
            arm_reset_gripping_to_shot()

            # 步骤4: 射击位置 -> 复位
            logger.info("[ArmLoadStoredDart] 步骤4: 射击位置 -> 复位")
            arm_shot_to_reset()

            logger.info("[ArmLoadStoredDart] 从复位位置加载存储的飞镖到发射区并返回复位完成")
            set_debug_var('arm_composite_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "加载存储飞镖到发射区成功")

            return True

        except Exception as e:
            logger.error(f"[ArmLoadStoredDart] 加载存储飞镖到发射区异常：{e}")
            set_debug_var('arm_composite_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "加载存储飞镖到发射区失败")
            return False