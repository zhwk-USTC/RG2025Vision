# Auto-generated. DO NOT EDIT MANUALLY.
# Generated at UTC 2025-09-05 09:07:35
# Version policy:
#   PROTOCOL_DATA_VER_FULL = YYYYMMDDHHMMSS (UTC)
#   PROTOCOL_DATA_VER      = PROTOCOL_DATA_VER_FULL & 0xFF  # 1-byte for DATA header

from enum import IntEnum
from typing import Dict

PROTOCOL_DATA_VER_FULL: int = 20250905090735
PROTOCOL_DATA_VER: int = 0xAF

class Msg(IntEnum):
    PC_TO_MCU = 0x01
    MCU_TO_PC = 0x02

class Var(IntEnum):
    TEST_VAR_F32 = 0x5D  # F32
    TEST_VAR_U8 = 0x67  # U8
    TEST_VAR_U16 = 0xE6  # U16

VAR_FIXED_SIZE: Dict[int, int] = {
    int(Var.TEST_VAR_F32): 4,
    int(Var.TEST_VAR_U8): 1,
    int(Var.TEST_VAR_U16): 2,
}

# BYTES 类型未在 VAR_FIXED_SIZE 中声明，按 TLV 的 L 作为长度处理。
