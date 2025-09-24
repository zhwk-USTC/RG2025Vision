from core.logger import logger
from ...debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class CounterGreaterEqual:
    """
    计数器大于等于条件节点
    检查指定计数器的值是否大于等于给定值
    """

    def __init__(self, context_key: str = "execution_count", value: int = 0):
        """
        构造计数器大于等于条件节点

        Args:
            context_key: 要检查的计数器在执行器上下文中的键名
            value: 要比较的值
        """
        self.context_key = context_key
        self.value = value

    def run(self) -> bool:
        """
        检查计数器是否大于等于指定值

        Returns:
            bool: 计数器值大于等于指定值时返回True，否则返回False
        """
        try:
            # 从TaskExecutor的execution_context获取计数器
            from ...executor.task_executor import _task_executor

            # 获取当前计数，如果不存在则初始化为0
            current_count = _task_executor.execution_context.get(self.context_key, 0)

            result = (current_count >= self.value)

            if result:
                logger.info(f"[CounterGreaterEqual] 计数器 '{self.context_key}' 值 {current_count} >= {self.value}，条件为True")
                set_debug_var('condition_counter_greater_equal', {
                    'context_key': self.context_key,
                    'current_value': current_count,
                    'threshold_value': self.value,
                    'decision': 'true'
                }, DebugLevel.INFO, DebugCategory.STATUS,
                f"计数器 '{self.context_key}' >= {self.value}，条件为True")
            else:
                logger.info(f"[CounterGreaterEqual] 计数器 '{self.context_key}' 值 {current_count} < {self.value}，条件为False")
                set_debug_var('condition_counter_greater_equal', {
                    'context_key': self.context_key,
                    'current_value': current_count,
                    'threshold_value': self.value,
                    'decision': 'false'
                }, DebugLevel.INFO, DebugCategory.STATUS,
                f"计数器 '{self.context_key}' < {self.value}，条件为False")

            return result

        except Exception as e:
            logger.error(f"[CounterGreaterEqual] 检查计数器异常: {e}")
            set_debug_var('condition_counter_greater_equal_error', {
                'context_key': self.context_key,
                'threshold_value': self.value,
                'error': str(e),
                'result': 'failed'
            }, DebugLevel.ERROR, DebugCategory.ERROR,
            f"检查计数器 '{self.context_key}' 时发生异常: {e}")
            return False