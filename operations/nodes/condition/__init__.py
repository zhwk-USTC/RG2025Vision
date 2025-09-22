from .jump import JUMP
from .check_last_task_result import CheckLastTaskResult

# 汇总所有条件类
_COND_NODE_CLASSES = {
    'jump': JUMP,
    'check_last_task_result': CheckLastTaskResult,
}