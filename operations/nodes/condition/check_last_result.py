from typing import Optional
from core.logger import logger
from ...debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class CheckLastResult:
    """
    检查上一个任务结果的条件节点
    逻辑：只有上一个任务明确失败(False)时返回False，其他情况都返回True
    """

    def __init__(self):
        """
        无参数构造
        """
        pass

    def run(self) -> bool:
        """
        检查上一个任务的结果
        逻辑：只有上一个任务明确失败(False)时返回False，其他情况(True、None、无结果)都返回True
        """
        try:
            # 尝试从TaskExecutor的execution_context获取上一个任务的结果
            from ...executor.task_executor import _task_executor

            last_result = _task_executor.execution_context.get('last_result')

            # 只有明确失败(False)时才返回False，其他情况都返回True
            if last_result is False:
                logger.info("[CheckLastTaskResult] 上一个任务失败，返回False")
                set_debug_var('condition_last_task_check', {
                    'last_result': last_result,
                    'decision': 'jump_to_error_handler'
                }, DebugLevel.INFO, DebugCategory.STATUS,
                "上一个任务失败，条件判断为False，跳转到错误处理")
                return False
            else:
                # True、None或其他值都认为是成功或未执行，继续流程
                result_desc = 'success' if last_result is True else 'none_or_unknown'
                logger.info(f"[CheckLastTaskResult] 上一个任务结果: {last_result} ({result_desc})，继续执行")
                set_debug_var('condition_last_task_check', {
                    'last_result': last_result,
                    'decision': 'continue_execution'
                }, DebugLevel.INFO, DebugCategory.STATUS,
                f"上一个任务结果为{result_desc}，条件判断为True，继续执行")
                return True

        except Exception as e:
            logger.error(f"[CheckLastTaskResult] 检查上一个任务结果时发生异常: {e}")
            set_debug_var('condition_last_task_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR,
                         f"检查上一个任务结果时发生异常: {e}")
            return False