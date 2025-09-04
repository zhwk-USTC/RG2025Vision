# Auto-generated. DO NOT EDIT MANUALLY.
# Generated at UTC 2025-09-04 00:29:44
# Version policy:
#   PROTOCOL_DATA_VER_FULL = YYYYMMDDHHMMSS (UTC)
#   PROTOCOL_DATA_VER      = PROTOCOL_DATA_VER_FULL & 0xFF  # 1-byte for DATA header

from enum import IntEnum
from typing import Dict

PROTOCOL_DATA_VER_FULL: int = 20250904002944
PROTOCOL_DATA_VER: int = 0x80

class Msg(IntEnum):
    PC_TO_MCU = 0x01
    MCU_TO_PC = 0x02

class Var(IntEnum):
    TEST1 = 0xA2  # U16LE
    TEST0 = 0xBD  # U8

VAR_FIXED_SIZE: Dict[int, int] = {
    int(Var.TEST1): 2,
    int(Var.TEST0): 1,
}

# BYTES 类型未在 VAR_FIXED_SIZE 中声明，按 TLV 的 L 作为长度处理。
