import operator
from core.logger import logger
from ...debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class CounterCompare:
    """
    计数器比较条件节点
    检查指定计数器的值与给定值的比较结果
    """

    # 支持的比较操作符映射
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
    }

    def __init__(self, context_key: str = "execution_count", operator: str = ">=", value: int = 0):
        """
        构造计数器比较条件节点

        Args:
            context_key: 要检查的计数器在执行器上下文中的键名
            operator: 比较操作符，支持 ==, !=, <, <=, >, >=
            value: 要比较的值
        """
        if operator not in self.OPERATORS:
            raise ValueError(f"不支持的比较操作符: {operator}。支持的操作符: {list(self.OPERATORS.keys())}")

        self.context_key = context_key
        self.operator = operator
        self.value = int(value)
        self._op_func = self.OPERATORS[operator]

    def run(self) -> bool:
        """
        检查计数器与指定值的比较结果

        Returns:
            bool: 比较结果为True时返回True，否则返回False
        """
        try:
            # 从TaskExecutor的execution_context获取计数器
            from ...executor.task_executor import _task_executor

            # 获取当前计数，如果不存在则初始化为0
            current_count = _task_executor.execution_context.get(self.context_key, 0)

            result = self._op_func(current_count, self.value)

            if result:
                logger.info(f"[CounterCompare] 计数器 '{self.context_key}' 值 {current_count} {self.operator} {self.value}，条件为True")
                set_debug_var('condition_counter_compare', {
                    'context_key': self.context_key,
                    'current_value': current_count,
                    'operator': self.operator,
                    'compare_value': self.value,
                    'decision': 'true'
                }, DebugLevel.INFO, DebugCategory.STATUS,
                f"计数器 '{self.context_key}' {self.operator} {self.value}，条件为True")
            else:
                logger.info(f"[CounterCompare] 计数器 '{self.context_key}' 值 {current_count} 不满足 {self.operator} {self.value}，条件为False")
                set_debug_var('condition_counter_compare', {
                    'context_key': self.context_key,
                    'current_value': current_count,
                    'operator': self.operator,
                    'compare_value': self.value,
                    'decision': 'false'
                }, DebugLevel.INFO, DebugCategory.STATUS,
                f"计数器 '{self.context_key}' 不满足 {self.operator} {self.value}，条件为False")

            return result

        except Exception as e:
            logger.error(f"[CounterCompare] 检查计数器异常: {e}")
            set_debug_var('condition_counter_compare_error', {
                'context_key': self.context_key,
                'operator': self.operator,
                'compare_value': self.value,
                'error': str(e),
                'result': 'failed'
            }, DebugLevel.ERROR, DebugCategory.ERROR,
            f"检查计数器 '{self.context_key}' 时发生异常: {e}")
            return False