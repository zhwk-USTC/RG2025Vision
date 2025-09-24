from typing import Optional
from core.logger import logger
from ...debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class InvertLastResult:
    """
    反转上一个任务结果的条件节点
    逻辑：反转上一个任务的结果，如果上一个是True则返回False，如果是False则返回True
    """

    def __init__(self):
        """
        无参数构造
        """
        pass

    def run(self) -> bool:
        """
        反转上一个任务的结果
        逻辑：True -> False, False -> True, None -> True (默认当作成功)
        """
        try:
            # 尝试从TaskExecutor的execution_context获取上一个任务的结果
            from ...executor.task_executor import _task_executor

            last_result = _task_executor.execution_context.get('last_result')

            # 反转结果
            if last_result is True:
                inverted = False
                decision = 'jump'
                logger.info("[InvertLastResult] 上一个任务成功，反转后返回False")
            elif last_result is False:
                inverted = True
                decision = 'continue'
                logger.info("[InvertLastResult] 上一个任务失败，反转后返回True")
            else:
                # None或其他未知值，默认当作成功，反转后为False
                inverted = False
                decision = 'jump'
                logger.info(f"[InvertLastResult] 上一个任务结果未知({last_result})，默认当作成功，反转后返回False")

            set_debug_var('condition_invert_last_result', {
                'last_result': last_result,
                'inverted_result': inverted,
                'decision': decision
            }, DebugLevel.INFO, DebugCategory.STATUS,
            f"反转上一个任务结果: {last_result} -> {inverted}")

            return inverted

        except Exception as e:
            logger.error(f"[InvertLastResult] 反转上一个任务结果时发生异常: {e}")
            set_debug_var('condition_invert_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR,
                         f"反转上一个任务结果时发生异常: {e}")
            return False