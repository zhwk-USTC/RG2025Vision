from .common.print import print_node
from .common.delay import delay
from .base_align_to_apriltag import BaseAlignToAprilTag
from .base import BaseMove, BaseRotate, BaseStop, BaseRotateByAngle
from .arm import (
    ArmReset,
    ArmHighToStore,
    ArmHighToShot,
    ArmHighToWait,
    ArmLowToStore,
    ArmLowToShot,
    ArmLowToWait,
    ArmStoreToShot,
    ArmWaitToShot
)
from .fire_once import FireOnce
from .common.system_cleanup import SystemCleanup
from .common.system_init import SystemInit
from .turret.turret_align_to_light import TurretAlignToLight
from .turret.turret_set_yaw import TurretSetYaw
from .turret.dart_push_once import DartPushOnce
from .turret.set_friction_wheel_speed import SetFrictionWheelSpeed
from .turret.friction_wheel_start import FrictionWheelStart
from .turret.friction_wheel_stop import FrictionWheelStop
from .common.counter_increment import CounterIncrement
from .common.counter_decrement import CounterDecrement
from .common.counter_set import CounterSet
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
    'arm_high_to_store': ArmHighToStore,
    'arm_high_to_shot': ArmHighToShot,
    'arm_high_to_wait': ArmHighToWait,
    'arm_low_to_store': ArmLowToStore,
    'arm_low_to_shot': ArmLowToShot,
    'arm_low_to_wait': ArmLowToWait,
    'arm_store_to_shot': ArmStoreToShot,
    'arm_wait_to_shot': ArmWaitToShot,
    'fire_once': FireOnce,
    'system_cleanup': SystemCleanup,
    'system_init': SystemInit,
    'turret_align_to_light': TurretAlignToLight,
    'turret_set_yaw': TurretSetYaw,
    'dart_push_once': DartPushOnce,
    'set_friction_wheel_speed': SetFrictionWheelSpeed,
    'friction_wheel_start': FrictionWheelStart,
    'friction_wheel_stop': FrictionWheelStop,
    'counter_increment': CounterIncrement,
    'counter_decrement': CounterDecrement,
    'counter_set': CounterSet,
    'set_camera_exposure': SetCameraExposure,
}