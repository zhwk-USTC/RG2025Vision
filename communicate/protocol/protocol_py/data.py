# data.py
# DATA = MSG(1B) | VER(1B) | TLVs...
# TLV  = T(1B)   | L(1B)   | V(L bytes)
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple, Union, Any

# 兼容包内相对导入与脚本式绝对导入
try:
    from .protocol_defs import Msg, Var, VAR_FIXED_SIZE  # type: ignore
except Exception:  # pragma: no cover
    from protocol_defs import Msg, Var, VAR_FIXED_SIZE  # type: ignore

BytesLike = Union[bytes, bytearray, memoryview]
VarId = Union[Var, int]


# -----------------------------
# 基础 TLV 编解码（宽容未知 T）
# -----------------------------
def encode_tlv(t: VarId, value: bytes) -> bytes:
    """
    编码单个 TLV 项。
    - t: Var 枚举或 0..255 的整数
    - value: 已经是字节序列（长度 0..255）
    """
    t_val = int(t) if isinstance(t, Var) else int(t)
    if not (0 <= t_val <= 0xFF):
        raise ValueError("T must be 0..255")
    if len(value) > 255:
        raise ValueError("TLV value too long (>255)")
    return bytes([t_val, len(value)]) + value


def decode_tlv(data: BytesLike) -> List[Tuple[Union[Var, int], bytes]]:
    """
    解码 TLV 字节流为 [(T, V), ...]
    - 对未知 T：返回原始整数，不抛异常，保证前向兼容
    """
    b = bytes(data)
    res: List[Tuple[Union[Var, int], bytes]] = []
    i = 0
    n = len(b)
    while i < n:
        if i + 2 > n:
            raise ValueError("invalid TLV header")
        t_raw = b[i]
        l = b[i + 1]
        if i + 2 + l > n:
            raise ValueError("invalid TLV length")
        v = b[i + 2 : i + 2 + l]
        try:
            t_val: Union[Var, int] = Var(t_raw)
        except ValueError:
            t_val = t_raw  # 未知变量ID，保持原样
        res.append((t_val, v))
        i += 2 + l
    return res


# -----------------------------
# DATA 头部 + TLV 序列 编解码
# -----------------------------
from .protocol_defs import Msg, PROTOCOL_DATA_VER
def encode_data(tlvs: Iterable[Tuple[VarId, bytes]], *,
                msg: Union[Msg, int] = Msg.PC_TO_MCU, ver: int = PROTOCOL_DATA_VER
                ) -> bytes:
    """
    打包 DATA：MSG | VER | TLVs...
    - msg: Msg 枚举或 0..255
    - ver: 0..255
    - tlvs: 可迭代 [(T, Vbytes)]
    """
    out = bytearray(2)
    out[0] = int(msg) if isinstance(msg, Msg) else (int(msg) & 0xFF)
    out[1] = ver & 0xFF
    for t, v in tlvs:
        out.extend(encode_tlv(t, v))
    return bytes(out)


def decode_data(data: BytesLike) -> Tuple[Union[Msg, int], int, List[Tuple[Union[Var, int], bytes]]]:
    """
    解析 DATA，返回三元组 (msg, ver, tlvs)
    - msg 若可识别则为 Msg 枚举，否则为原始整数
    - tlvs 为 [(Var或int, bytes)]
    """
    b = bytes(data)
    if len(b) < 2:
        raise ValueError("DATA too short")
    msg_raw = b[0]
    try:
        msg: Union[Msg, int] = Msg(msg_raw)
    except ValueError:
        msg = msg_raw
    ver = b[1]
    tlv_list = decode_tlv(b[2:]) if len(b) > 2 else []
    return msg, ver, tlv_list


# -----------------------------
# 便捷：按“变量-值”编码
# -----------------------------
def _pack_fixed_le(value: Union[int, bool], size: int) -> bytes:
    """把 int/bool 按小端、固定字节数打包。size ∈ {1,2,4}。"""
    if isinstance(value, bool):
        iv = 1 if value else 0
    elif isinstance(value, int):
        iv = value
    else:
        raise TypeError("fixed-width variable expected int/bool value")
    if size == 1:
        return bytes([iv & 0xFF])
    if size == 2:
        return (iv & 0xFFFF).to_bytes(2, "little")
    if size == 4:
        return (iv & 0xFFFFFFFF).to_bytes(4, "little")
    raise ValueError(f"unsupported fixed size: {size}")


def encode_var(t: VarId, value: Union[int, bool, bytes, bytearray, memoryview]) -> bytes:
    """
    以“变量 + Python 值”的方式编码 TLV：
    - 若该变量在 VAR_FIXED_SIZE 中声明了固定字节数（1/2/4），
      则可直接传入 int/bool，将自动按小端打包；
    - 若是可变长（未出现在 VAR_FIXED_SIZE），请传入 bytes-like。
    """
    t_id = int(t) if isinstance(t, Var) else int(t)
    size: int | None = VAR_FIXED_SIZE.get(t_id)
    if size is None:
        # 可变长：要求用户直接给 bytes
        if isinstance(value, (bytes, bytearray, memoryview)):
            vbytes = bytes(value)
        else:
            raise TypeError(f"variable 0x{t_id:02X} is variable-length; please provide bytes")
    else:
        # 固定长：允许 int/bool，也允许 bytes，但长度需匹配
        if isinstance(value, (bytes, bytearray, memoryview)):
            vbytes = bytes(value)
            if len(vbytes) != size:
                raise ValueError(f"fixed-width var 0x{t_id:02X} requires {size} bytes, got {len(vbytes)}")
        else:
            vbytes = _pack_fixed_le(value, size)
    return encode_tlv(t_id, vbytes)


def encode_kv(msg: Union[Msg, int], ver: int,
              kv: Dict[VarId, Union[int, bool, bytes, bytearray, memoryview]]) -> bytes:
    """
    把 {变量: 值} 字典直接打包成 DATA。
    - 固定长变量：值可为 int/bool/bytes（bytes 长度需匹配）
    - 可变长变量：值必须为 bytes-like
    """
    tlvs = (encode_var(t, v) for t, v in kv.items())
    # 先拼好 TLV，再一次性写入 DATA
    tlv_bytes = b"".join(tlvs)
    return encode_data([], msg=msg, ver=ver) + tlv_bytes  # 为避免重复遍历，直接拼接更快


# -----------------------------
# 便捷：把 TLV 的 V 解码成 Python 值
# -----------------------------
def value_of(t: VarId, v: BytesLike) -> Union[int, bytes]:
    """
    将 TLV 的 V 还原为 Python 值：
    - 若该变量是固定宽度（1/2/4），按小端转成 int
    - 否则返回原始 bytes
    """
    t_id = int(t) if isinstance(t, Var) else int(t)
    b = bytes(v)
    size = VAR_FIXED_SIZE.get(t_id)
    if size is None:
        return b
    if size == 1:
        return b[0] if b else 0
    if size == 2:
        if len(b) != 2:
            raise ValueError(f"expect 2 bytes for var 0x{t_id:02X}, got {len(b)}")
        return int.from_bytes(b, "little")
    if size == 4:
        if len(b) != 4:
            raise ValueError(f"expect 4 bytes for var 0x{t_id:02X}, got {len(b)}")
        return int.from_bytes(b, "little")
    # 其它固定值（理论上不会出现）
    if len(b) != size:
        raise ValueError(f"expect {size} bytes for var 0x{t_id:02X}, got {len(b)}")
    return int.from_bytes(b, "little")
