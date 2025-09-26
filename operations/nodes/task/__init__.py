from .common.print import print_node
from .common.delay import delay
from .base_align_to_apriltag import BaseAlignToAprilTag
from .base import BaseMove, BaseRotate, BaseStop, BaseRotateByAngle
from .arm import (
    ArmReset,
    ArmResetToLowPrepare, ArmLowPrepareToLowGrip, ArmLowGripToResetGripping,
    ArmResetToHighPrepare, ArmHighPrepareToHighGrip, ArmHighGripToResetGripping,
    ArmResetGrippingToStore, ArmResetGrippingToShot, ArmStoreToResetGripping,
    ArmStoreToReset, ArmResetToStore, ArmShotToReset,
    ArmPickLowDart, ArmPickHighDart, ArmStoreDart, ArmShootDart, ArmLoadStoredDart
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
    'arm_reset_to_low_prepare': ArmResetToLowPrepare,
    'arm_low_prepare_to_low_grip': ArmLowPrepareToLowGrip,
    'arm_low_grip_to_reset_gripping': ArmLowGripToResetGripping,
    'arm_reset_to_high_prepare': ArmResetToHighPrepare,
    'arm_high_prepare_to_high_grip': ArmHighPrepareToHighGrip,
    'arm_high_grip_to_reset_gripping': ArmHighGripToResetGripping,
    'arm_reset_gripping_to_store': ArmResetGrippingToStore,
    'arm_reset_gripping_to_shot': ArmResetGrippingToShot,
    'arm_store_to_reset_gripping': ArmStoreToResetGripping,
    'arm_store_to_reset': ArmStoreToReset,
    'arm_reset_to_store': ArmResetToStore,
    'arm_shot_to_reset': ArmShotToReset,
    'arm_pick_low_dart': ArmPickLowDart,
    'arm_pick_high_dart': ArmPickHighDart,
    'arm_store_dart': ArmStoreDart,
    'arm_shoot_dart': ArmShootDart,
    'arm_load_stored_dart': ArmLoadStoredDart,
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