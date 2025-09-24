from core.logger import logger
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class CounterGet:
    """
    获取计数器任务节点
    用于获取指定计数器的当前值，并将其设置为 last_result
    """

    def __init__(self, context_key: str = "execution_count"):
        """
        构造获取计数器任务节点

        Args:
            context_key: 要获取的计数器在执行器上下文中的键名
        """
        self.context_key = context_key

    def run(self) -> bool:
        """
        获取指定的计数器值并设置为 last_result

        Returns:
            bool: 总是返回True（获取操作总是成功）
        """
        try:
            # 从TaskExecutor的execution_context获取计数器
            from ....executor.task_executor import _task_executor

            # 获取当前计数，如果不存在则初始化为0
            current_count = _task_executor.execution_context.get(self.context_key, 0)

            # 将计数器值设置为 last_result（通过返回值的布尔转换）
            # 注意：这里我们返回计数器值，但执行器会将其转换为布尔值
            # 所以我们需要特殊处理 - 直接设置 last_result

            # 手动设置 last_result
            _task_executor.execution_context['last_result'] = current_count

            logger.info(f"[CounterGet] 获取计数器 '{self.context_key}' 的值: {current_count}")
            set_debug_var('task_counter_get', {
                'context_key': self.context_key,
                'value': current_count,
                'result': 'success'
            }, DebugLevel.INFO, DebugCategory.STATUS,
            f"获取计数器 '{self.context_key}' 的值: {current_count}")

            # 返回 True 表示任务成功，但实际值通过 last_result 传递
            return True

        except Exception as e:
            logger.error(f"[CounterGet] 获取计数器异常: {e}")
            set_debug_var('task_counter_get_error', {
                'context_key': self.context_key,
                'error': str(e),
                'result': 'failed'
            }, DebugLevel.ERROR, DebugCategory.ERROR,
            f"获取计数器 '{self.context_key}' 时发生异常: {e}")
            return False