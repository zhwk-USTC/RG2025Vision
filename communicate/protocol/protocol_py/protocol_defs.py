# Auto-generated. DO NOT EDIT MANUALLY.
# Generated at UTC 2025-09-17 07:11:55
# Version policy:
#   PROTOCOL_DATA_VER_FULL = YYYYMMDDHHMMSS (UTC)
#   PROTOCOL_DATA_VER      = PROTOCOL_DATA_VER_FULL & 0xFF  # 1-byte for DATA header

from enum import IntEnum
from typing import Dict, Optional, TypedDict

PROTOCOL_DATA_VER_FULL: int = 20250917071155
PROTOCOL_DATA_VER: int = 0x33

class Msg(IntEnum):
    PC_TO_MCU = 0x01
    MCU_TO_PC = 0x02

class Var(IntEnum):
    FRICTION_WHEEL_SPEED = 0x01  # F32
    DEBUG_RIGHT_FRONT_WHEEL_PWM = 0x04  # U16
    GRIPPER_TAG_Y = 0x15  # F32
    DEBUG_ARM_ZHONGBI_PWM = 0x1A  # U16
    BASE_MOVE_BACKWARD_FAST = 0x21  # BOOL
    DEBUG_RIGHT_REAR_WHEEL_PWM = 0x25  # U16
    DEBUG_ARM_GRIPPER_PWM = 0x26  # U16
    DEBUG_DART_PUSH_STOP = 0x30  # BOOL
    DEBUG_FRICTION_WHEEL_START = 0x32  # BOOL
    BASE_ROTATE_CW_FAST = 0x36  # BOOL
    DEBUG_RIGHT_REAR_WHEEL_DIR = 0x3A  # U8
    FIRE_ONCE = 0x41  # BOOL
    ARM_RESET = 0x4B  # BOOL
    BASE_MOVE_FORWARD_FAST = 0x5B  # BOOL
    BASE_ROTATE_CW_SLOW = 0x5D  # BOOL
    DEBUG_ARM_DI_PWM = 0x5F  # U16
    TEST_VAR_U8 = 0x67  # U8
    GRIPPER_TAG_X = 0x69  # F32
    DATA_ERROR = 0x6A  # U8
    DEBUG_LEFT_FRONT_WHEEL_PWM = 0x6C  # U16
    DEBUG_DART_PUSH_FORWARD = 0x6D  # BOOL
    DEBUG_ARM_DABI_PWM = 0x71  # U16
    ARM_RELAX = 0x72  # BOOL
    DEBUG_ARM_XIAOBI_PWM = 0x75  # U16
    DEBUG_DART_PUSH_BACKWARD = 0x79  # BOOL
    DEBUG_LEFT_REAR_WHEEL_PWM = 0x7A  # U16
    BASE_STOP = 0x7B  # BOOL
    BASE_ROTATE_CCW_FAST = 0x83  # BOOL
    DEBUG_ARM_SHOUWAN_PWM = 0x84  # U16
    TEST_VAR_F32 = 0x88  # F32
    BASE_MOVE_FORWARD_SLOW = 0x8C  # BOOL
    ARM_RESET_TO_PREPARE = 0x8D  # BOOL
    DEBUG_FRICTION_WHEEL_STOP = 0x92  # BOOL
    BASE_ROTATE_CCW_SLOW = 0x94  # BOOL
    ARM_GRASP_DART = 0x95  # BOOL
    BASE_MOVE_BACKWARD_SLOW = 0x99  # BOOL
    BASE_MOVE_LEFT_SLOW = 0x9A  # BOOL
    HEARTBEAT = 0xA6  # U8
    DEBUG_GRIPPER_GRASP = 0xAA  # BOOL
    DEBUG_RIGHT_FRONT_WHEEL_DIR = 0xAD  # U8
    DEBUG_DART_PUSH_RESET = 0xBF  # BOOL
    GRIPPER_TAG_Z = 0xC4  # F32
    BASE_MOVE_LEFT_FAST = 0xC5  # BOOL
    DEBUG_GRIPPER_RELEASE = 0xC8  # BOOL
    BASE_MOVE_RIGHT_SLOW = 0xC9  # BOOL
    BASE_MOVE_RIGHT_FAST = 0xCA  # BOOL
    DEBUG_LEFT_REAR_WHEEL_DIR = 0xD1  # U8
    ARM_LOAD_DART = 0xE0  # BOOL
    TURRET_ANGLE_YAW = 0xE1  # F32
    DEBUG_DART_PUSH_ONCE = 0xE4  # BOOL
    TEST_VAR_U16 = 0xE6  # U16
    DEBUG_LEFT_FRONT_WHEEL_DIR = 0xEA  # U8

class VarMeta(TypedDict, total=False):
    key: str       # 原始键（YAML 中的 name，用于 UI/业务）
    vtype: str     # 变量类型字符串（如 U16LE/F32/…）
    size: Optional[int]  # 固定长度；可变长(BYTES/STR/…)为 None

VAR_META: Dict[int, VarMeta] = {
    int(Var.FRICTION_WHEEL_SPEED): {"key": "friction_wheel_speed", "vtype": "F32", "size": 4},
    int(Var.DEBUG_RIGHT_FRONT_WHEEL_PWM): {"key": "debug_right_front_wheel_pwm", "vtype": "U16", "size": 2},
    int(Var.GRIPPER_TAG_Y): {"key": "gripper_tag_y", "vtype": "F32", "size": 4},
    int(Var.DEBUG_ARM_ZHONGBI_PWM): {"key": "debug_arm_zhongbi_pwm", "vtype": "U16", "size": 2},
    int(Var.BASE_MOVE_BACKWARD_FAST): {"key": "base_move_backward_fast", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_RIGHT_REAR_WHEEL_PWM): {"key": "debug_right_rear_wheel_pwm", "vtype": "U16", "size": 2},
    int(Var.DEBUG_ARM_GRIPPER_PWM): {"key": "debug_arm_gripper_pwm", "vtype": "U16", "size": 2},
    int(Var.DEBUG_DART_PUSH_STOP): {"key": "debug_dart_push_stop", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_FRICTION_WHEEL_START): {"key": "debug_friction_wheel_start", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CW_FAST): {"key": "base_rotate_CW_fast", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_RIGHT_REAR_WHEEL_DIR): {"key": "debug_right_rear_wheel_dir", "vtype": "U8", "size": 1},
    int(Var.FIRE_ONCE): {"key": "fire_once", "vtype": "BOOL", "size": 1},
    int(Var.ARM_RESET): {"key": "arm_reset", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_FORWARD_FAST): {"key": "base_move_forward_fast", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CW_SLOW): {"key": "base_rotate_CW_slow", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_ARM_DI_PWM): {"key": "debug_arm_di_pwm", "vtype": "U16", "size": 2},
    int(Var.TEST_VAR_U8): {"key": "test_var_u8", "vtype": "U8", "size": 1},
    int(Var.GRIPPER_TAG_X): {"key": "gripper_tag_x", "vtype": "F32", "size": 4},
    int(Var.DATA_ERROR): {"key": "DATA_ERROR", "vtype": "U8", "size": 1},
    int(Var.DEBUG_LEFT_FRONT_WHEEL_PWM): {"key": "debug_left_front_wheel_pwm", "vtype": "U16", "size": 2},
    int(Var.DEBUG_DART_PUSH_FORWARD): {"key": "debug_dart_push_forward", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_ARM_DABI_PWM): {"key": "debug_arm_dabi_pwm", "vtype": "U16", "size": 2},
    int(Var.ARM_RELAX): {"key": "arm_relax", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_ARM_XIAOBI_PWM): {"key": "debug_arm_xiaobi_pwm", "vtype": "U16", "size": 2},
    int(Var.DEBUG_DART_PUSH_BACKWARD): {"key": "debug_dart_push_backward", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_LEFT_REAR_WHEEL_PWM): {"key": "debug_left_rear_wheel_pwm", "vtype": "U16", "size": 2},
    int(Var.BASE_STOP): {"key": "base_stop", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CCW_FAST): {"key": "base_rotate_CCW_fast", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_ARM_SHOUWAN_PWM): {"key": "debug_arm_shouwan_pwm", "vtype": "U16", "size": 2},
    int(Var.TEST_VAR_F32): {"key": "test_var_f32", "vtype": "F32", "size": 4},
    int(Var.BASE_MOVE_FORWARD_SLOW): {"key": "base_move_forward_slow", "vtype": "BOOL", "size": 1},
    int(Var.ARM_RESET_TO_PREPARE): {"key": "arm_reset_to_prepare", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_FRICTION_WHEEL_STOP): {"key": "debug_friction_wheel_stop", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CCW_SLOW): {"key": "base_rotate_CCW_slow", "vtype": "BOOL", "size": 1},
    int(Var.ARM_GRASP_DART): {"key": "arm_grasp_dart", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_BACKWARD_SLOW): {"key": "base_move_backward_slow", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_LEFT_SLOW): {"key": "base_move_left_slow", "vtype": "BOOL", "size": 1},
    int(Var.HEARTBEAT): {"key": "HEARTBEAT", "vtype": "U8", "size": 1},
    int(Var.DEBUG_GRIPPER_GRASP): {"key": "debug_gripper_grasp", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_RIGHT_FRONT_WHEEL_DIR): {"key": "debug_right_front_wheel_dir", "vtype": "U8", "size": 1},
    int(Var.DEBUG_DART_PUSH_RESET): {"key": "debug_dart_push_reset", "vtype": "BOOL", "size": 1},
    int(Var.GRIPPER_TAG_Z): {"key": "gripper_tag_z", "vtype": "F32", "size": 4},
    int(Var.BASE_MOVE_LEFT_FAST): {"key": "base_move_left_fast", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_GRIPPER_RELEASE): {"key": "debug_gripper_release", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_RIGHT_SLOW): {"key": "base_move_right_slow", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_RIGHT_FAST): {"key": "base_move_right_fast", "vtype": "BOOL", "size": 1},
    int(Var.DEBUG_LEFT_REAR_WHEEL_DIR): {"key": "debug_left_rear_wheel_dir", "vtype": "U8", "size": 1},
    int(Var.ARM_LOAD_DART): {"key": "arm_load_dart", "vtype": "BOOL", "size": 1},
    int(Var.TURRET_ANGLE_YAW): {"key": "turret_angle_yaw", "vtype": "F32", "size": 4},
    int(Var.DEBUG_DART_PUSH_ONCE): {"key": "debug_dart_push_once", "vtype": "BOOL", "size": 1},
    int(Var.TEST_VAR_U16): {"key": "test_var_u16", "vtype": "U16", "size": 2},
    int(Var.DEBUG_LEFT_FRONT_WHEEL_DIR): {"key": "debug_left_front_wheel_dir", "vtype": "U8", "size": 1},
}

VAR_FIXED_SIZE: Dict[int, int] = {
    int(Var.FRICTION_WHEEL_SPEED): 4,
    int(Var.DEBUG_RIGHT_FRONT_WHEEL_PWM): 2,
    int(Var.GRIPPER_TAG_Y): 4,
    int(Var.DEBUG_ARM_ZHONGBI_PWM): 2,
    int(Var.BASE_MOVE_BACKWARD_FAST): 1,
    int(Var.DEBUG_RIGHT_REAR_WHEEL_PWM): 2,
    int(Var.DEBUG_ARM_GRIPPER_PWM): 2,
    int(Var.DEBUG_DART_PUSH_STOP): 1,
    int(Var.DEBUG_FRICTION_WHEEL_START): 1,
    int(Var.BASE_ROTATE_CW_FAST): 1,
    int(Var.DEBUG_RIGHT_REAR_WHEEL_DIR): 1,
    int(Var.FIRE_ONCE): 1,
    int(Var.ARM_RESET): 1,
    int(Var.BASE_MOVE_FORWARD_FAST): 1,
    int(Var.BASE_ROTATE_CW_SLOW): 1,
    int(Var.DEBUG_ARM_DI_PWM): 2,
    int(Var.TEST_VAR_U8): 1,
    int(Var.GRIPPER_TAG_X): 4,
    int(Var.DATA_ERROR): 1,
    int(Var.DEBUG_LEFT_FRONT_WHEEL_PWM): 2,
    int(Var.DEBUG_DART_PUSH_FORWARD): 1,
    int(Var.DEBUG_ARM_DABI_PWM): 2,
    int(Var.ARM_RELAX): 1,
    int(Var.DEBUG_ARM_XIAOBI_PWM): 2,
    int(Var.DEBUG_DART_PUSH_BACKWARD): 1,
    int(Var.DEBUG_LEFT_REAR_WHEEL_PWM): 2,
    int(Var.BASE_STOP): 1,
    int(Var.BASE_ROTATE_CCW_FAST): 1,
    int(Var.DEBUG_ARM_SHOUWAN_PWM): 2,
    int(Var.TEST_VAR_F32): 4,
    int(Var.BASE_MOVE_FORWARD_SLOW): 1,
    int(Var.ARM_RESET_TO_PREPARE): 1,
    int(Var.DEBUG_FRICTION_WHEEL_STOP): 1,
    int(Var.BASE_ROTATE_CCW_SLOW): 1,
    int(Var.ARM_GRASP_DART): 1,
    int(Var.BASE_MOVE_BACKWARD_SLOW): 1,
    int(Var.BASE_MOVE_LEFT_SLOW): 1,
    int(Var.HEARTBEAT): 1,
    int(Var.DEBUG_GRIPPER_GRASP): 1,
    int(Var.DEBUG_RIGHT_FRONT_WHEEL_DIR): 1,
    int(Var.DEBUG_DART_PUSH_RESET): 1,
    int(Var.GRIPPER_TAG_Z): 4,
    int(Var.BASE_MOVE_LEFT_FAST): 1,
    int(Var.DEBUG_GRIPPER_RELEASE): 1,
    int(Var.BASE_MOVE_RIGHT_SLOW): 1,
    int(Var.BASE_MOVE_RIGHT_FAST): 1,
    int(Var.DEBUG_LEFT_REAR_WHEEL_DIR): 1,
    int(Var.ARM_LOAD_DART): 1,
    int(Var.TURRET_ANGLE_YAW): 4,
    int(Var.DEBUG_DART_PUSH_ONCE): 1,
    int(Var.TEST_VAR_U16): 2,
    int(Var.DEBUG_LEFT_FRONT_WHEEL_DIR): 1,
}

# 说明：
# - BYTES/STR 等可变长类型不在 VAR_FIXED_SIZE 中；按 TLV 的 L 解析。
# - 编解码逻辑由其他模块实现；此文件仅提供 ID/类型/长度元信息。
