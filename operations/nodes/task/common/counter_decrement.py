from core.logger import logger
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class CounterDecrement:
    """
    减少计数器任务节点
    用于减少指定计数器的值
    """

    def __init__(self, context_key: str = "execution_count", decrement: int = 1):
        """
        构造减少计数器任务节点

        Args:
            context_key: 要操作的计数器在执行器上下文中的键名
            decrement: 减少的值（默认为1）
        """
        self.context_key = context_key
        self.decrement = decrement

    def run(self) -> bool:
        """
        减少指定的计数器

        Returns:
            bool: 总是返回True（减少操作总是成功）
        """
        try:
            # 从TaskExecutor的execution_context获取并减少计数器
            from ....executor.task_executor import _task_executor

            # 获取当前计数，如果不存在则初始化为0
            current_count = _task_executor.execution_context.get(self.context_key, 0)

            # 减少计数器
            new_count = current_count - self.decrement

            # 更新上下文中的计数器
            _task_executor.execution_context[self.context_key] = new_count

            logger.info(f"[CounterDecrement] 计数器 '{self.context_key}' 从 {current_count} 减少到 {new_count}")
            set_debug_var('task_counter_decrement', {
                'context_key': self.context_key,
                'previous_value': current_count,
                'decrement': self.decrement,
                'new_value': new_count,
                'result': 'success'
            }, DebugLevel.INFO, DebugCategory.STATUS,
            f"计数器 '{self.context_key}' 减少 {self.decrement}，当前值: {new_count}")

            return True

        except Exception as e:
            logger.error(f"[CounterDecrement] 减少计数器异常: {e}")
            set_debug_var('task_counter_decrement_error', {
                'context_key': self.context_key,
                'decrement': self.decrement,
                'error': str(e),
                'result': 'failed'
            }, DebugLevel.ERROR, DebugCategory.ERROR,
            f"减少计数器 '{self.context_key}' 时发生异常: {e}")
            return False