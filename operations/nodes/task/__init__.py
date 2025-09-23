from .common.print import print_node
from .common.delay import delay
from .base_align_to_apriltag import BaseAlignToAprilTag
from .base import BaseMove, BaseRotate, BaseStop, BaseRotateByAngle
from .arm import ArmReset, ArmPrepare, ArmGrasp, ArmLoad, ArmGraspAndLoad
from .fire_control import FireControl
from .common.system_cleanup import SystemCleanup
from .common.system_init import SystemInit
from .turret_align_to_light import TurretAlignToLight
from .reset_counter import ResetCounter

# 汇总所有任务节点类
_TASK_NODE_CLASSES = {
    'print': print_node,
    'delay': delay,
    'base_align_to_apriltag': BaseAlignToAprilTag,
    'base_move': BaseMove,
    'base_rotate': BaseRotate,
    'base_stop': BaseStop,
    'base_rotate_by_angle': BaseRotateByAngle,
    'arm_reset': ArmReset,
    'arm_prepare': ArmPrepare,
    'arm_grasp': ArmGrasp,
    'arm_load': ArmLoad,
    'arm_grasp_and_load': ArmGraspAndLoad,
    'fire_control': FireControl,
    'system_cleanup': SystemCleanup,
    'system_init': SystemInit,
    'turret_align_to_light': TurretAlignToLight,
    'reset_counter': ResetCounter,
}