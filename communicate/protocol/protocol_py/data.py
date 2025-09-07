# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple, Union, Any, Optional
import struct

from .protocol_defs import Msg, Var, VAR_FIXED_SIZE, PROTOCOL_DATA_VER, VAR_META

BytesLike = Union[bytes, bytearray, memoryview]
VarId = Union[Var, int]

# ===============================
# 基础工具
# ===============================
def _u8(x: int) -> int:
    return x & 0xFF

def _as_bytes(b: BytesLike) -> bytes:
    return bytes(b) if not isinstance(b, bytes) else b

def _pack_fixed_le_int_bool(value: Union[int, bool], size: int) -> bytes:
    """把 int/bool 按小端定长(1/2/4/…size)打包。"""
    if isinstance(value, bool):
        iv = 1 if value else 0
    elif isinstance(value, int):
        iv = value
    else:
        raise TypeError("fixed-width variable expects int/bool")
    if size not in (1, 2, 4):
        # 兜底也可以支持其它 size
        return int(iv & ((1 << (8 * size)) - 1)).to_bytes(size, "little")
    if size == 1:
        return bytes([iv & 0xFF])
    if size == 2:
        return (iv & 0xFFFF).to_bytes(2, "little")
    if size == 4:
        return (iv & 0xFFFFFFFF).to_bytes(4, "little")
    raise AssertionError("unreachable")

def _unpack_fixed_le_int(b: bytes) -> int:
    return int.from_bytes(b, "little")

def _pack_value_for_size(value: Union[int, bool, float, BytesLike], size: int) -> bytes:
    """
    按固定宽度打包：
      - float 且 size==4 → IEEE754 float32 (little-endian)
      - bytes-like → 长度必须与 size 一致
      - 其余（int/bool）按小端定长
    """
    if isinstance(value, float):
        if size != 4:
            raise TypeError(f"float value only supported for 4-byte variables (got size={size})")
        return struct.pack("<f", value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        vbytes = _as_bytes(value)
        if len(vbytes) != size:
            raise ValueError(f"fixed-width requires {size} bytes, got {len(vbytes)}")
        return vbytes
    # int / bool
    return _pack_fixed_le_int_bool(value, size)

def _as_float32_le(b: BytesLike) -> float:
    bb = _as_bytes(b)
    if len(bb) != 4:
        raise ValueError(f"expect 4 bytes for float32, got {len(bb)}")
    return struct.unpack("<f", bb)[0]

# ===============================
# 数据结构
# ===============================
@dataclass(frozen=True)
class TLV:
    t: Union[Var, int]
    v: bytes

    def __iter__(self):
        yield self.t
        yield self.v

@dataclass(frozen=True)
class DataPacket:
    msg: Union[Msg, int]
    ver: int
    tlvs: List[TLV]

# ===============================
# TLV 编码/解码（无状态）
# ===============================
class TLVEncoder:
    """TLV 项编码（宽容未知 T，长度 0..255）。"""

    @staticmethod
    def encode_tlv(t: VarId, value: BytesLike) -> bytes:
        t_val = int(t) if isinstance(t, Var) else int(t)
        if not (0 <= t_val <= 0xFF):
            raise ValueError("T must be 0..255")
        vbytes = _as_bytes(value)
        if len(vbytes) > 0xFF:
            raise ValueError("TLV value too long (>255)")
        return bytes((t_val, len(vbytes))) + vbytes

class TLVDecoder:
    """TLV 字节流解码为 TLV 列表（未知 T 返回原始整数）。"""

    @staticmethod
    def decode_tlvs(data: BytesLike) -> List[TLV]:
        b = _as_bytes(data)
        res: List[TLV] = []
        i, n = 0, len(b)
        while i < n:
            if i + 2 > n:
                raise ValueError("invalid TLV header")
            t_raw = b[i]
            l = b[i + 1]
            end = i + 2 + l
            if end > n:
                raise ValueError("invalid TLV length")
            v = b[i + 2 : end]
            try:
                t_val: Union[Var, int] = Var(t_raw)
            except ValueError:
                t_val = t_raw  # 未知变量，保留原值
            res.append(TLV(t_val, v))
            i = end
        return res

# ===============================
# DATA (MSG|VER|TLVs...) 编解码
# ===============================
class DataEncoder:
    """打包 DATA：MSG(1) | VER(1) | TLVs...。不做流式。"""

    def __init__(self, *, default_msg: Union[Msg, int] = Msg.PC_TO_MCU, default_ver: int = PROTOCOL_DATA_VER):
        self.default_msg = int(default_msg) if isinstance(default_msg, Msg) else _u8(int(default_msg))
        self.default_ver = _u8(default_ver)

    def encode(self, tlvs: Iterable[Tuple[VarId, BytesLike]] | Iterable[TLV],
               *, msg: Union[Msg, int] | None = None, ver: int | None = None) -> bytes:
        m = self.default_msg if msg is None else (int(msg) if isinstance(msg, Msg) else _u8(int(msg)))
        v = self.default_ver if ver is None else _u8(ver)

        out = bytearray((m, v))
        for item in tlvs:
            if isinstance(item, TLV):
                t, vb = item.t, item.v
                out.extend(TLVEncoder.encode_tlv(t, vb))
            else:
                t, vb = item  # Tuple[VarId, BytesLike]
                out.extend(TLVEncoder.encode_tlv(t, vb))
        return bytes(out)

    # 便捷：按 {变量: Python值} 直接编码（支持 float32）
    def encode_kv(self, kv: Dict[VarId, Union[int, bool, float, BytesLike]],
                  *, msg: Union[Msg, int] | None = None, ver: int | None = None) -> bytes:
        tlv_bytes = bytearray()

        for t, value in kv.items():
            t_id = int(t) if isinstance(t, Var) else int(t)

            meta = VAR_META.get(t_id)
            size = VAR_FIXED_SIZE.get(t_id)

            if size is None:
                # 变长：必须 bytes-like
                if not isinstance(value, (bytes, bytearray, memoryview)):
                    raise TypeError(f"variable 0x{t_id:02X} is variable-length; please provide bytes")
                vbytes = _as_bytes(value)
            else:
                # 固定宽度：按 size 打包（保留你现有的小端+float32策略）
                vbytes = _pack_value_for_size(value, size)

            tlv_bytes.extend(TLVEncoder.encode_tlv(t_id, vbytes))

        # 拼接 MSG|VER|TLVs
        m = self.default_msg if msg is None else (int(msg) if isinstance(msg, Msg) else _u8(int(msg)))
        v = self.default_ver if ver is None else _u8(ver)
        return bytes((m, v)) + bytes(tlv_bytes)

class DataDecoder:
    """解析 DATA → DataPacket；提供将 TLV 的 V 还原成 Python 值的便捷函数。"""

    @staticmethod
    def decode(data: BytesLike) -> DataPacket:
        b = _as_bytes(data)
        if len(b) < 2:
            raise ValueError("DATA too short")
        msg_raw = b[0]
        try:
            msg: Union[Msg, int] = Msg(msg_raw)
        except ValueError:
            msg = msg_raw
        ver = b[1]
        tlvs = TLVDecoder.decode_tlvs(b[2:]) if len(b) > 2 else []
        return DataPacket(msg=msg, ver=ver, tlvs=tlvs)

    @staticmethod
    def value_of(t: VarId, v: BytesLike) -> Union[int, float, bytes]:
        """
        将 TLV 的 V 还原为 Python 值：
          - 变量为可变长：返回 bytes
          - 固定宽度：
              * as_float=True 且 size==4 → 返回 float32（小端）
              * 否则返回 int（小端）
        """
        t_id = int(t) if isinstance(t, Var) else int(t)
        b = _as_bytes(v)
        
        meta = VAR_META.get(t_id)
        size = VAR_FIXED_SIZE.get(t_id)
        if size is None or meta is None:
            return b
        if len(b) != size:
            raise ValueError(f"expect {size} bytes for var 0x{t_id:02X}, got {len(b)}")

        vtype = (meta.get("vtype") or "").upper()
        # 这里保留小端默认
        if vtype in ("F32", "F32LE"):
            return _as_float32_le(b)
        # 其它按无符号小端整型还原（如需区分有符号/BE，可再细分）
        return _unpack_fixed_le_int(b)

    @staticmethod
    def value_as_float32(v: BytesLike) -> float:
        """辅助函数：把 4 字节小端解释为 float32。"""
        return _as_float32_le(v)

# ===============================
# 薄门面（可选）：统一入口
# ===============================
class DataCodec:
    """组合式门面：对外暴露 encode / decode / value_of。"""
    __slots__ = ("enc", "dec")

    def __init__(self, *, default_msg: Union[Msg, int] = Msg.PC_TO_MCU, default_ver: int = PROTOCOL_DATA_VER):
        self.enc = DataEncoder(default_msg=default_msg, default_ver=default_ver)
        self.dec = DataDecoder()

    def encode(self, tlvs: Iterable[Tuple[VarId, BytesLike]] | Iterable[TLV],
               *, msg: Union[Msg, int] | None = None, ver: int | None = None) -> bytes:
        return self.enc.encode(tlvs, msg=msg, ver=ver)

    def encode_kv(self, kv: Dict[VarId, Union[int, bool, float, BytesLike]],
                  *, msg: Union[Msg, int] | None = None, ver: int | None = None) -> bytes:
        return self.enc.encode_kv(kv, msg=msg, ver=ver)

    def decode(self, data: BytesLike) -> DataPacket:
        return self.dec.decode(data)

    def value_of(self, t: VarId, v: BytesLike) -> Union[int, float, bytes]:
        return self.dec.value_of(t, v)

    def value_as_float32(self, v: BytesLike) -> float:
        return self.dec.value_as_float32(v)
