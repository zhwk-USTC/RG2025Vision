from .print import print_node
from .delay import delay
from .base_align_to_apriltag import BaseAlignToAprilTag
from .base.base_move import BaseMove
from .base.base_rotate import BaseRotate
from .base.base_stop import BaseStop
from .arm import ArmReset, ArmPrepare, ArmGrasp, ArmLoad, ArmGraspAndLoad
from .fire_control import FireControl
from .system_cleanup import SystemCleanup
from .system_init import SystemInit
from .turret_align_to_light import TurretAlignToLight

# 汇总所有任务节点类
_TASK_NODE_CLASSES = {
    'print': print_node,
    'delay': delay,
    'base_align_to_apriltag': BaseAlignToAprilTag,
    'base_move': BaseMove,
    'base_rotate': BaseRotate,
    'base_stop': BaseStop,
    'arm_reset': ArmReset,
    'arm_prepare': ArmPrepare,
    'arm_grasp': ArmGrasp,
    'arm_load': ArmLoad,
    'arm_grasp_and_load': ArmGraspAndLoad,
    'fire_control': FireControl,
    'system_cleanup': SystemCleanup,
    'system_init': SystemInit,
    'turret_align_to_light': TurretAlignToLight,
}