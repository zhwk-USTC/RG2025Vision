from core.logger import logger
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class ResetCounter:
    """
    重置执行计数器任务节点
    用于重置CountLimit条件节点使用的计数器
    """

    def __init__(self, context_key: str = "execution_count"):
        """
        构造重置执行计数器任务节点

        Args:
            context_key: 要重置的计数器在执行器上下文中的键名
        """
        self.context_key = context_key

    def run(self) -> bool:
        """
        重置指定的计数器

        Returns:
            bool: 总是返回True（重置操作总是成功）
        """
        try:
            # 从TaskExecutor的execution_context重置计数器
            from ....executor.task_executor import _task_executor

            # 将计数器重置为0
            _task_executor.execution_context[self.context_key] = 0

            logger.info(f"[ResetCounter] 计数器 '{self.context_key}' 已重置为0")
            set_debug_var('task_reset_counter', {
                'context_key': self.context_key,
                'reset_value': 0,
                'result': 'success'
            }, DebugLevel.INFO, DebugCategory.STATUS,
            f"执行计数器 '{self.context_key}' 已重置为0")

            return True

        except Exception as e:
            logger.error(f"[ResetCounter] 重置计数器异常: {e}")
            set_debug_var('task_reset_counter_error', {
                'context_key': self.context_key,
                'error': str(e),
                'result': 'failed'
            }, DebugLevel.ERROR, DebugCategory.ERROR,
            f"重置执行计数器 '{self.context_key}' 时发生异常: {e}")
            return False