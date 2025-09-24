from core.logger import logger
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class CounterSet:
    """
    设置计数器任务节点
    用于将计数器设置为指定的值
    """

    def __init__(self, context_key: str = "execution_count", value: int = 0):
        """
        构造设置计数器任务节点

        Args:
            context_key: 要操作的计数器在执行器上下文中的键名
            value: 要设置的值
        """
        self.context_key = context_key
        self.value = value

    def run(self) -> bool:
        """
        设置指定的计数器为指定值

        Returns:
            bool: 总是返回True（设置操作总是成功）
        """
        try:
            # 从TaskExecutor的execution_context设置计数器
            from ....executor.task_executor import _task_executor

            # 获取当前计数，用于日志
            previous_value = _task_executor.execution_context.get(self.context_key, 0)

            # 设置计数器为指定值
            _task_executor.execution_context[self.context_key] = self.value

            logger.info(f"[CounterSet] 计数器 '{self.context_key}' 从 {previous_value} 设置为 {self.value}")
            set_debug_var('task_counter_set', {
                'context_key': self.context_key,
                'previous_value': previous_value,
                'new_value': self.value,
                'result': 'success'
            }, DebugLevel.INFO, DebugCategory.STATUS,
            f"计数器 '{self.context_key}' 设置为 {self.value}")

            return True

        except Exception as e:
            logger.error(f"[CounterSet] 设置计数器异常: {e}")
            set_debug_var('task_counter_set_error', {
                'context_key': self.context_key,
                'target_value': self.value,
                'error': str(e),
                'result': 'failed'
            }, DebugLevel.ERROR, DebugCategory.ERROR,
            f"设置计数器 '{self.context_key}' 时发生异常: {e}")
            return False