# Auto-generated. DO NOT EDIT MANUALLY.
# Generated at UTC 2025-09-25 10:27:03
# Version policy:
#   PROTOCOL_DATA_VER_FULL = YYYYMMDDHHMMSS (UTC)
#   PROTOCOL_DATA_VER      = PROTOCOL_DATA_VER_FULL & 0xFF  # 1-byte for DATA header

from enum import IntEnum
from typing import Dict, Optional, TypedDict

PROTOCOL_DATA_VER_FULL: int = 20250925102703
PROTOCOL_DATA_VER: int = 0x6F

class Msg(IntEnum):
    PC_TO_MCU = 0x01
    MCU_TO_PC = 0x02

class Var(IntEnum):
    FRICTION_WHEEL_SPEED = 0x01  # F32
    ARM_SHOT_TO_RESET = 0x10  # BOOL
    ARM_HIGH_GRIP_TO_RESET_GRIPPING = 0x18  # BOOL
    ARM_RESET_GRIPPING_TO_SHOT = 0x19  # BOOL
    TEST_VAR_U8 = 0x1C  # U8
    BASE_MOVE_BACKWARD_FAST = 0x21  # BOOL
    ARM_LOW_GRIP_TO_RESET_GRIPPING = 0x26  # BOOL
    BASE_MOVE_FORWARD_FAST_EX = 0x29  # BOOL
    ARM_RESET_TO_HIGH_PREPARE = 0x2E  # BOOL
    ARM_LOW_PREPARE_TO_LOW_GRIP = 0x30  # BOOL
    ARM_RESET_GRIPPING_TO_STORE = 0x32  # BOOL
    BASE_ROTATE_CW_FAST = 0x36  # BOOL
    FIRE_ONCE = 0x41  # BOOL
    ARM_RESET = 0x4B  # BOOL
    BASE_MOVE_FORWARD_FAST = 0x5B  # BOOL
    BASE_ROTATE_CW_SLOW = 0x5D  # BOOL
    IMU_YAW = 0x67  # F32
    ARM_RELAX = 0x72  # BOOL
    BASE_STOP = 0x7B  # BOOL
    BASE_ROTATE_CCW_FAST = 0x83  # BOOL
    TEST_VAR_F32 = 0x88  # F32
    BASE_MOVE_FORWARD_SLOW = 0x8C  # BOOL
    ERROR = 0x93  # U8
    BASE_ROTATE_CCW_SLOW = 0x94  # BOOL
    BASE_MOVE_BACKWARD_SLOW = 0x99  # BOOL
    BASE_MOVE_LEFT_SLOW = 0x9A  # BOOL
    OK = 0x9D  # U8
    BASE_MOVE_BACKWARD_FAST_EX = 0x9F  # BOOL
    GET_IMU_YAW = 0xA3  # BOOL
    IMU_RESET = 0xA4  # BOOL
    FRICTION_WHEEL_STOP = 0xA6  # BOOL
    ARM_HIGH_PREPARE_TO_HIGH_GRIP = 0xAA  # BOOL
    BASE_MOVE_LEFT_FAST = 0xC5  # BOOL
    BASE_MOVE_RIGHT_SLOW = 0xC9  # BOOL
    BASE_MOVE_RIGHT_FAST = 0xCA  # BOOL
    DART_PUSH_ONCE = 0xCD  # BOOL
    ARM_STORE_TO_RESET_GRIPPING = 0xCF  # BOOL
    HEARTBEAT = 0xD1  # U8
    ARM_RESET_TO_LOW_PREPARE = 0xD8  # BOOL
    FRICTION_WHEEL_START = 0xDE  # BOOL
    TURRET_ANGLE_YAW = 0xE1  # F32
    TEST_VAR_U16 = 0xE6  # U16
    ARM_STORE_TO_RESET = 0xEB  # BOOL

class VarMeta(TypedDict, total=False):
    key: str       # 原始键（YAML 中的 name，用于 UI/业务）
    vtype: str     # 变量类型字符串（如 U16LE/F32/…）
    size: Optional[int]  # 固定长度；可变长(BYTES/STR/…)为 None

VAR_META: Dict[int, VarMeta] = {
    int(Var.FRICTION_WHEEL_SPEED): {"key": "friction_wheel_speed", "vtype": "F32", "size": 4},
    int(Var.ARM_SHOT_TO_RESET): {"key": "arm_shot_to_reset", "vtype": "BOOL", "size": 1},
    int(Var.ARM_HIGH_GRIP_TO_RESET_GRIPPING): {"key": "arm_high_grip_to_reset_gripping", "vtype": "BOOL", "size": 1},
    int(Var.ARM_RESET_GRIPPING_TO_SHOT): {"key": "arm_reset_gripping_to_shot", "vtype": "BOOL", "size": 1},
    int(Var.TEST_VAR_U8): {"key": "test_var_u8", "vtype": "U8", "size": 1},
    int(Var.BASE_MOVE_BACKWARD_FAST): {"key": "base_move_backward_fast", "vtype": "BOOL", "size": 1},
    int(Var.ARM_LOW_GRIP_TO_RESET_GRIPPING): {"key": "arm_low_grip_to_reset_gripping", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_FORWARD_FAST_EX): {"key": "base_move_forward_fast_ex", "vtype": "BOOL", "size": 1},
    int(Var.ARM_RESET_TO_HIGH_PREPARE): {"key": "arm_reset_to_high_prepare", "vtype": "BOOL", "size": 1},
    int(Var.ARM_LOW_PREPARE_TO_LOW_GRIP): {"key": "arm_low_prepare_to_low_grip", "vtype": "BOOL", "size": 1},
    int(Var.ARM_RESET_GRIPPING_TO_STORE): {"key": "arm_reset_gripping_to_store", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CW_FAST): {"key": "base_rotate_CW_fast", "vtype": "BOOL", "size": 1},
    int(Var.FIRE_ONCE): {"key": "fire_once", "vtype": "BOOL", "size": 1},
    int(Var.ARM_RESET): {"key": "arm_reset", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_FORWARD_FAST): {"key": "base_move_forward_fast", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CW_SLOW): {"key": "base_rotate_CW_slow", "vtype": "BOOL", "size": 1},
    int(Var.IMU_YAW): {"key": "imu_yaw", "vtype": "F32", "size": 4},
    int(Var.ARM_RELAX): {"key": "arm_relax", "vtype": "BOOL", "size": 1},
    int(Var.BASE_STOP): {"key": "base_stop", "vtype": "BOOL", "size": 1},
    int(Var.BASE_ROTATE_CCW_FAST): {"key": "base_rotate_CCW_fast", "vtype": "BOOL", "size": 1},
    int(Var.TEST_VAR_F32): {"key": "test_var_f32", "vtype": "F32", "size": 4},
    int(Var.BASE_MOVE_FORWARD_SLOW): {"key": "base_move_forward_slow", "vtype": "BOOL", "size": 1},
    int(Var.ERROR): {"key": "ERROR", "vtype": "U8", "size": 1},
    int(Var.BASE_ROTATE_CCW_SLOW): {"key": "base_rotate_CCW_slow", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_BACKWARD_SLOW): {"key": "base_move_backward_slow", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_LEFT_SLOW): {"key": "base_move_left_slow", "vtype": "BOOL", "size": 1},
    int(Var.OK): {"key": "OK", "vtype": "U8", "size": 1},
    int(Var.BASE_MOVE_BACKWARD_FAST_EX): {"key": "base_move_backward_fast_ex", "vtype": "BOOL", "size": 1},
    int(Var.GET_IMU_YAW): {"key": "get_imu_yaw", "vtype": "BOOL", "size": 1},
    int(Var.IMU_RESET): {"key": "imu_reset", "vtype": "BOOL", "size": 1},
    int(Var.FRICTION_WHEEL_STOP): {"key": "friction_wheel_stop", "vtype": "BOOL", "size": 1},
    int(Var.ARM_HIGH_PREPARE_TO_HIGH_GRIP): {"key": "arm_high_prepare_to_high_grip", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_LEFT_FAST): {"key": "base_move_left_fast", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_RIGHT_SLOW): {"key": "base_move_right_slow", "vtype": "BOOL", "size": 1},
    int(Var.BASE_MOVE_RIGHT_FAST): {"key": "base_move_right_fast", "vtype": "BOOL", "size": 1},
    int(Var.DART_PUSH_ONCE): {"key": "dart_push_once", "vtype": "BOOL", "size": 1},
    int(Var.ARM_STORE_TO_RESET_GRIPPING): {"key": "arm_store_to_reset_gripping", "vtype": "BOOL", "size": 1},
    int(Var.HEARTBEAT): {"key": "HEARTBEAT", "vtype": "U8", "size": 1},
    int(Var.ARM_RESET_TO_LOW_PREPARE): {"key": "arm_reset_to_low_prepare", "vtype": "BOOL", "size": 1},
    int(Var.FRICTION_WHEEL_START): {"key": "friction_wheel_start", "vtype": "BOOL", "size": 1},
    int(Var.TURRET_ANGLE_YAW): {"key": "turret_angle_yaw", "vtype": "F32", "size": 4},
    int(Var.TEST_VAR_U16): {"key": "test_var_u16", "vtype": "U16", "size": 2},
    int(Var.ARM_STORE_TO_RESET): {"key": "arm_store_to_reset", "vtype": "BOOL", "size": 1},
}

VAR_FIXED_SIZE: Dict[int, int] = {
    int(Var.FRICTION_WHEEL_SPEED): 4,
    int(Var.ARM_SHOT_TO_RESET): 1,
    int(Var.ARM_HIGH_GRIP_TO_RESET_GRIPPING): 1,
    int(Var.ARM_RESET_GRIPPING_TO_SHOT): 1,
    int(Var.TEST_VAR_U8): 1,
    int(Var.BASE_MOVE_BACKWARD_FAST): 1,
    int(Var.ARM_LOW_GRIP_TO_RESET_GRIPPING): 1,
    int(Var.BASE_MOVE_FORWARD_FAST_EX): 1,
    int(Var.ARM_RESET_TO_HIGH_PREPARE): 1,
    int(Var.ARM_LOW_PREPARE_TO_LOW_GRIP): 1,
    int(Var.ARM_RESET_GRIPPING_TO_STORE): 1,
    int(Var.BASE_ROTATE_CW_FAST): 1,
    int(Var.FIRE_ONCE): 1,
    int(Var.ARM_RESET): 1,
    int(Var.BASE_MOVE_FORWARD_FAST): 1,
    int(Var.BASE_ROTATE_CW_SLOW): 1,
    int(Var.IMU_YAW): 4,
    int(Var.ARM_RELAX): 1,
    int(Var.BASE_STOP): 1,
    int(Var.BASE_ROTATE_CCW_FAST): 1,
    int(Var.TEST_VAR_F32): 4,
    int(Var.BASE_MOVE_FORWARD_SLOW): 1,
    int(Var.ERROR): 1,
    int(Var.BASE_ROTATE_CCW_SLOW): 1,
    int(Var.BASE_MOVE_BACKWARD_SLOW): 1,
    int(Var.BASE_MOVE_LEFT_SLOW): 1,
    int(Var.OK): 1,
    int(Var.BASE_MOVE_BACKWARD_FAST_EX): 1,
    int(Var.GET_IMU_YAW): 1,
    int(Var.IMU_RESET): 1,
    int(Var.FRICTION_WHEEL_STOP): 1,
    int(Var.ARM_HIGH_PREPARE_TO_HIGH_GRIP): 1,
    int(Var.BASE_MOVE_LEFT_FAST): 1,
    int(Var.BASE_MOVE_RIGHT_SLOW): 1,
    int(Var.BASE_MOVE_RIGHT_FAST): 1,
    int(Var.DART_PUSH_ONCE): 1,
    int(Var.ARM_STORE_TO_RESET_GRIPPING): 1,
    int(Var.HEARTBEAT): 1,
    int(Var.ARM_RESET_TO_LOW_PREPARE): 1,
    int(Var.FRICTION_WHEEL_START): 1,
    int(Var.TURRET_ANGLE_YAW): 4,
    int(Var.TEST_VAR_U16): 2,
    int(Var.ARM_STORE_TO_RESET): 1,
}

# 说明：
# - BYTES/STR 等可变长类型不在 VAR_FIXED_SIZE 中；按 TLV 的 L 解析。
# - 编解码逻辑由其他模块实现；此文件仅提供 ID/类型/长度元信息。
