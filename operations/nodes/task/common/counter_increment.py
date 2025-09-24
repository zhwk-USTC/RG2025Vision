from core.logger import logger
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class CounterIncrement:
    """
    增加计数器任务节点
    用于增加指定计数器的值
    """

    def __init__(self, context_key: str = "execution_count", increment: int = 1):
        """
        构造增加计数器任务节点

        Args:
            context_key: 要操作的计数器在执行器上下文中的键名
            increment: 增加的值（默认为1）
        """
        self.context_key = context_key
        self.increment = increment

    def run(self) -> bool:
        """
        增加指定的计数器

        Returns:
            bool: 总是返回True（增加操作总是成功）
        """
        try:
            # 从TaskExecutor的execution_context获取并增加计数器
            from ....executor.task_executor import _task_executor

            # 获取当前计数，如果不存在则初始化为0
            current_count = _task_executor.execution_context.get(self.context_key, 0)

            # 增加计数器
            new_count = current_count + self.increment

            # 更新上下文中的计数器
            _task_executor.execution_context[self.context_key] = new_count

            logger.info(f"[CounterIncrement] 计数器 '{self.context_key}' 从 {current_count} 增加到 {new_count}")
            set_debug_var('task_counter_increment', {
                'context_key': self.context_key,
                'previous_value': current_count,
                'increment': self.increment,
                'new_value': new_count,
                'result': 'success'
            }, DebugLevel.INFO, DebugCategory.STATUS,
            f"计数器 '{self.context_key}' 增加 {self.increment}，当前值: {new_count}")

            return True

        except Exception as e:
            logger.error(f"[CounterIncrement] 增加计数器异常: {e}")
            set_debug_var('task_counter_increment_error', {
                'context_key': self.context_key,
                'increment': self.increment,
                'error': str(e),
                'result': 'failed'
            }, DebugLevel.ERROR, DebugCategory.ERROR,
            f"增加计数器 '{self.context_key}' 时发生异常: {e}")
            return False