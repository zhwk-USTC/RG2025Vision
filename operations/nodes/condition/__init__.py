from .jump import JUMP
from .check_last_result import CheckLastResult
from .counter_compare import CounterCompare
from .invert_last_result import InvertLastResult

# 汇总所有条件类
_COND_NODE_CLASSES = {
    'true': JUMP,
    'counter_compare': CounterCompare,
    'last_failure': InvertLastResult,
    'last_success': CheckLastResult,
}