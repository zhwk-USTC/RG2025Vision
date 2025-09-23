from .common.print import print_node
from .common.delay import delay
from .base_align_to_apriltag import BaseAlignToAprilTag
from .base import BaseMove, BaseRotate, BaseStop, BaseRotateByAngle
from .arm import ArmReset, ArmPrepare, ArmGrasp, ArmLoad, ArmGraspAndLoad
from .fire_once import FireOnce
from .common.system_cleanup import SystemCleanup
from .common.system_init import SystemInit
from .turret.turret_align_to_light import TurretAlignToLight
from .turret.turret_set_yaw import TurretSetYaw
from .common.reset_counter import ResetCounter
from .common.set_camera_exposure import SetCameraExposure

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
    'fire_control': FireOnce,
    'system_cleanup': SystemCleanup,
    'system_init': SystemInit,
    'turret_align_to_light': TurretAlignToLight,
    'turret_set_yaw': TurretSetYaw,
    'reset_counter': ResetCounter,
    'set_camera_exposure': SetCameraExposure,
}