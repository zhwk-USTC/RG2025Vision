from .jump import JUMP
from .check_last_result import CheckLastResult
from .counter_equals import CounterEquals
from .counter_greater_equal import CounterGreaterEqual
from .invert_last_result import InvertLastResult

# 汇总所有条件类
_COND_NODE_CLASSES = {
    'jump': JUMP,
    'jump_on_last_failure': CheckLastResult,
    'counter_equals': CounterEquals,
    'counter_greater_equal': CounterGreaterEqual,
    'jump_on_last_success': InvertLastResult,
}