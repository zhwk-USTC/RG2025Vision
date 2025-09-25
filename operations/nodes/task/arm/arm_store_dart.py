from core.logger import logger
from ....utils.communicate_utils import (
    arm_reset_gripping_to_store,
    arm_store_to_reset
)
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ArmStoreDart:
    """
    复合task：存储飞镖并返回复位
    抓取复位 -> 存储 -> 复位
    """

    def __init__(self):
        pass

    def run(self) -> bool:
        logger.info("[ArmStoreDart] 开始执行存储飞镖并返回复位")

        try:
            set_debug_var('arm_composite_action', 'store_dart',
                         DebugLevel.INFO, DebugCategory.CONTROL, "复合动作：存储飞镖")

            # 步骤1: 抓取复位 -> 存储
            logger.info("[ArmStoreDart] 步骤1: 抓取复位 -> 存储")
            arm_reset_gripping_to_store()

            # 步骤2: 存储 -> 复位
            logger.info("[ArmStoreDart] 步骤2: 存储 -> 复位")
            arm_store_to_reset()

            logger.info("[ArmStoreDart] 存储飞镖并返回复位完成")
            set_debug_var('arm_composite_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "存储飞镖动作成功")

            return True

        except Exception as e:
            logger.error(f"[ArmStoreDart] 存储飞镖异常：{e}")
            set_debug_var('arm_composite_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "存储飞镖动作失败")
            return False