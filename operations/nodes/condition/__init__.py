from .jump import JUMP
from .check_last_result import CheckLastResult
from .counter_equals import CounterEquals
from .counter_greater_equal import CounterGreaterEqual

# 汇总所有条件类
_COND_NODE_CLASSES = {
    'jump': JUMP,
    'check_last_result': CheckLastResult,
    'counter_equals': CounterEquals,
    'counter_greater_equal': CounterGreaterEqual,
}