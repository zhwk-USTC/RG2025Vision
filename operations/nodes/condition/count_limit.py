from core.logger import logger
from ...debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class CountLimit:
    """
    执行次数限制条件节点
    逻辑：执行次数未达到限制前返回True，达到限制后一直返回False
    计数器状态存储在执行器上下文中，确保状态在流程执行期间保持
    """

    def __init__(self, max_executions: int = 1, context_key: str = "execution_count"):
        """
        构造执行次数限制条件节点

        Args:
            max_executions: 最大执行次数，达到此次数后返回False
            context_key: 在执行器上下文中存储计数器的键名
        """
        self.max_executions = max_executions
        self.context_key = context_key

    def run(self) -> bool:
        """
        执行计数检查
        计数器状态从执行器上下文读取和写入

        Returns:
            bool: 当前计数 < 最大执行次数时返回True，否则返回False
        """
        try:
            # 从TaskExecutor的execution_context获取计数器
            from ...executor.task_executor import _task_executor

            # 获取当前计数，如果不存在则初始化为0
            current_count = _task_executor.execution_context.get(self.context_key, 0)

            # 计数器加1
            current_count += 1

            # 更新上下文中的计数器
            _task_executor.execution_context[self.context_key] = current_count

            if current_count <= self.max_executions:
                logger.info(f"[CountLimit] 执行次数: {current_count}/{self.max_executions}，条件为True")
                set_debug_var('condition_count_limit', {
                    'current_count': current_count,
                    'max_executions': self.max_executions,
                    'context_key': self.context_key,
                    'decision': 'continue'
                }, DebugLevel.INFO, DebugCategory.STATUS,
                f"执行次数 {current_count}/{self.max_executions}，条件为True，继续执行")
                return True
            else:
                logger.info(f"[CountLimit] 执行次数: {current_count}/{self.max_executions}，已达到限制，条件为False")
                set_debug_var('condition_count_limit', {
                    'current_count': current_count,
                    'max_executions': self.max_executions,
                    'context_key': self.context_key,
                    'decision': 'stop'
                }, DebugLevel.WARNING, DebugCategory.STATUS,
                f"执行次数 {current_count}/{self.max_executions}，已达到限制，条件为False")
                return False

        except Exception as e:
            logger.error(f"[CountLimit] 访问执行器上下文异常: {e}")
            set_debug_var('condition_count_limit_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR,
                         f"执行次数限制条件访问上下文异常: {e}")
            return False