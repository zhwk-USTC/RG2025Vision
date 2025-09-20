from .move_forward import MoveForward
from .print import print_node
from .delay import delay
from .base_align_to_apriltag import BaseAlignToAprilTag

# 汇总所有任务节点类
_TASK_NODE_CLASSES = {
    'move_forward': MoveForward,
    'print': print_node,
    'delay': delay,
    'base_align_to_apriltag': BaseAlignToAprilTag,
}