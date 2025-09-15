# Auto-generated. DO NOT EDIT MANUALLY.
# Generated at UTC 2025-09-15 16:01:50
# Version policy:
#   PROTOCOL_DATA_VER_FULL = YYYYMMDDHHMMSS (UTC)
#   PROTOCOL_DATA_VER      = PROTOCOL_DATA_VER_FULL & 0xFF  # 1-byte for DATA header

from enum import IntEnum
from typing import Dict, Optional, TypedDict

PROTOCOL_DATA_VER_FULL: int = 20250915160150
PROTOCOL_DATA_VER: int = 0x56

class Msg(IntEnum):
    PC_TO_MCU = 0x01
    MCU_TO_PC = 0x02

class Var(IntEnum):
    FRICTION_WHEEL_SPEED = 0x01  # F32
    GRIPPER_RELEASE = 0x04  # BOOL
    GRIPPER_TAG_Y = 0x15  # F32
    DART_PUSH_BACKWARD = 0x18  # BOOL
    BASE_MOVE_BACKWARD_FAST = 0x21  # BOOL
    BASE_ROTATE_CW_FAST = 0x36  # BOOL
    DART_PUSH_FORWARD = 0x49  # BOOL
    BASE_MOVE_FORWARD_FAST = 0x5B  # BOOL
    BASE_ROTATE_CW_SLOW = 0x5D  # BOOL
    DART_PUSH_STOP = 0x64  # BOOL
    TEST_VAR_U8 = 0x67  # U8
    GRIPPER_TAG_X = 0x69  # F32
    DATA_ERROR = 0x6A  # U8
    BASE_STOP = 0x7B  # BOOL
    BASE_ROTATE_CCW_FAST = 0x83  # BOOL
    TEST_VAR_F32 = 0x88  # F32
    BASE_MOVE_FORWARD_SLOW = 0x8C  # BOOL
    BASE_ROTATE_CCW_SLOW = 0x94  # BOOL
    BASE_MOVE_BACKWARD_SLOW = 0x99  # BOOL
    BASE_MOVE_LEFT_SLOW = 0x9A  # BOOL
    FRICTION_WHEEL_STOP = 0xA6  # BOOL
    GRIPPER_TAG_Z = 0xC4  # F32
    BASE_MOVE_LEFT_FAST = 0xC5  # BOOL
    BASE_MOVE_RIGHT_SLOW = 0xC9  # BOOL
    BASE_MOVE_RIGHT_FAST = 0xCA  # BOOL
    HEARTBEAT = 0xD1  # U8
    FRICTION_WHEEL_START = 0xDE  # BOOL
    TURRET_ANGLE_YAW = 0xE1  # F32
    TEST_VAR_U16 = 0xE6  # U16
    GRIPPER_GRASP = 0xEE  # BOOL

class VarMeta(TypedDict, total=False):
    key: str       # 原始键（YAML 中的 name，用于 UI/业务）
    vtype: str     # 变量类型字符串（如 U16LE/F32/…）
    size: Optional[int]  # 固定长度；可变长(BYTES/STR/…)为 None

VAR_META: Dict[int, VarMeta] = {
    int(Var.FRICTION_WHEEL_SPEED): {"key": "friction_wheel_speed", "vtype": "F32", "size": 4},
    int(Var.GRIPPER_RELEASE): {"key": "gripper_release", "vtype": "BOOL", "size": 1},
    int(Var.GRIPPER_TAG_Y): {"key": "gripper_tag_y", "vtype": "F32", "size": 4},
    int(Var.DART_PUSH_BACKWARD): {"key": "dart_push_backward", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_BACKWARD_FAST): {"key": "base_move_backward_fast", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CW_FAST): {"key": "base_rotate_CW_fast", "vtype": "BOOL", "size": 1},
    int(Var.DART_PUSH_FORWARD): {"key": "dart_push_forward", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_FORWARD_FAST): {"key": "base_move_forward_fast", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CW_SLOW): {"key": "base_rotate_CW_slow", "vtype": "BOOL", "size": 1},
    int(Var.DART_PUSH_STOP): {"key": "dart_push_stop", "vtype": "BOOL", "size": 1},
    int(Var.TEST_VAR_U8): {"key": "test_var_u8", "vtype": "U8", "size": 1},
    int(Var.GRIPPER_TAG_X): {"key": "gripper_tag_x", "vtype": "F32", "size": 4},
    int(Var.DATA_ERROR): {"key": "DATA_ERROR", "vtype": "U8", "size": 1},
    int(Var.BASE_STOP): {"key": "base_stop", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CCW_FAST): {"key": "base_rotate_CCW_fast", "vtype": "BOOL", "size": 1},
    int(Var.TEST_VAR_F32): {"key": "test_var_f32", "vtype": "F32", "size": 4},
    int(Var.BASE_MOVE_FORWARD_SLOW): {"key": "base_move_forward_slow", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CCW_SLOW): {"key": "base_rotate_CCW_slow", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_BACKWARD_SLOW): {"key": "base_move_backward_slow", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_LEFT_SLOW): {"key": "base_move_left_slow", "vtype": "BOOL", "size": 1},
    int(Var.FRICTION_WHEEL_STOP): {"key": "friction_wheel_stop", "vtype": "BOOL", "size": 1},
    int(Var.GRIPPER_TAG_Z): {"key": "gripper_tag_z", "vtype": "F32", "size": 4},
    int(Var.BASE_MOVE_LEFT_FAST): {"key": "base_move_left_fast", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_RIGHT_SLOW): {"key": "base_move_right_slow", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_RIGHT_FAST): {"key": "base_move_right_fast", "vtype": "BOOL", "size": 1},
    int(Var.HEARTBEAT): {"key": "HEARTBEAT", "vtype": "U8", "size": 1},
    int(Var.FRICTION_WHEEL_START): {"key": "friction_wheel_start", "vtype": "BOOL", "size": 1},
    int(Var.TURRET_ANGLE_YAW): {"key": "turret_angle_yaw", "vtype": "F32", "size": 4},
    int(Var.TEST_VAR_U16): {"key": "test_var_u16", "vtype": "U16", "size": 2},
    int(Var.GRIPPER_GRASP): {"key": "gripper_grasp", "vtype": "BOOL", "size": 1},
}

VAR_FIXED_SIZE: Dict[int, int] = {
    int(Var.FRICTION_WHEEL_SPEED): 4,
    int(Var.GRIPPER_RELEASE): 1,
    int(Var.GRIPPER_TAG_Y): 4,
    int(Var.DART_PUSH_BACKWARD): 1,
    int(Var.BASE_MOVE_BACKWARD_FAST): 1,
    int(Var.BASE_ROTATE_CW_FAST): 1,
    int(Var.DART_PUSH_FORWARD): 1,
    int(Var.BASE_MOVE_FORWARD_FAST): 1,
    int(Var.BASE_ROTATE_CW_SLOW): 1,
    int(Var.DART_PUSH_STOP): 1,
    int(Var.TEST_VAR_U8): 1,
    int(Var.GRIPPER_TAG_X): 4,
    int(Var.DATA_ERROR): 1,
    int(Var.BASE_STOP): 1,
    int(Var.BASE_ROTATE_CCW_FAST): 1,
    int(Var.TEST_VAR_F32): 4,
    int(Var.BASE_MOVE_FORWARD_SLOW): 1,
    int(Var.BASE_ROTATE_CCW_SLOW): 1,
    int(Var.BASE_MOVE_BACKWARD_SLOW): 1,
    int(Var.BASE_MOVE_LEFT_SLOW): 1,
    int(Var.FRICTION_WHEEL_STOP): 1,
    int(Var.GRIPPER_TAG_Z): 4,
    int(Var.BASE_MOVE_LEFT_FAST): 1,
    int(Var.BASE_MOVE_RIGHT_SLOW): 1,
    int(Var.BASE_MOVE_RIGHT_FAST): 1,
    int(Var.HEARTBEAT): 1,
    int(Var.FRICTION_WHEEL_START): 1,
    int(Var.TURRET_ANGLE_YAW): 4,
    int(Var.TEST_VAR_U16): 2,
    int(Var.GRIPPER_GRASP): 1,
}

# 说明：
# - BYTES/STR 等可变长类型不在 VAR_FIXED_SIZE 中；按 TLV 的 L 解析。
# - 编解码逻辑由其他模块实现；此文件仅提供 ID/类型/长度元信息。
