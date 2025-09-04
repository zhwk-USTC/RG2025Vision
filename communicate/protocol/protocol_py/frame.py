# -*- coding: utf-8 -*-
"""
Frame builder for PC<->MCU serial protocol (build-only)
Frame: AA | LEN | VER | SEQ | CHK | DATA... | 55

- LEN = 3 + N   (VER + SEQ + CHK + DATA)
- CHK = (LEN + VER + SEQ + sum(DATA bytes)) & 0xFF   # CHK 本身不参与
"""

from typing import Union

# bytes-like 类型统一定义
BytesLike = Union[bytes, bytearray, memoryview]

# 帧头和帧尾
FRAME_HEAD = 0xAA
FRAME_TAIL = 0x55

# 协议版本
VERSION = 0x00

# LEN 为 1 字节，LEN = 3 + N  => N 最大 252
MAX_DATA_LEN = 0xFF - 3  # 252


def u8(x: int) -> int:
    """裁剪到 0..255"""
    return x & 0xFF


def _as_byte_view(b: BytesLike) -> memoryview:
    """
    将任意 bytes-like 转为逐“字节”的 memoryview（不拷贝）。
    若原视图元素宽度>1，则 cast('B')；若 cast 不可用则退化到 bytes 拷贝。
    """
    mv = memoryview(b)
    try:
        return mv.cast('B')
    except TypeError:
        # 极少数对象 cast 可能失败，退化为 bytes 拷贝后再取视图
        return memoryview(bytes(b))


def _sum_bytes(data: BytesLike) -> int:
    """按字节求和，兼容 memoryview 的非 'B' 格式。"""
    mv = _as_byte_view(data)
    return sum(mv)


def checksum(len_byte: int, ver: int, seq: int, data: BytesLike) -> int:
    """CHK = (LEN + VER + SEQ + sum(DATA bytes)) & 0xFF"""
    s = u8(len_byte) + u8(ver) + u8(seq) + _sum_bytes(data)
    return u8(s)


def build_frame(seq: int, data: BytesLike = b"", ver: int = VERSION) -> bytes:
    """
    构建一帧：AA LEN VER SEQ CHK DATA... 55
    :param seq:  0..255
    :param data: 负载(字节序列)；如果需要“类型/命令”，请把它作为 DATA 的首字节等方式承载
    :param ver:  版本号
    :return: 完整帧 bytes
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like")

    data_mv = _as_byte_view(data)
    data_len = len(data_mv)  # 按“字节数”，而不是元素数

    if data_len > MAX_DATA_LEN:
        raise ValueError(f"data too long: {data_len} > {MAX_DATA_LEN}")

    length = 3 + data_len  # VER + SEQ + CHK + DATA
    chk = checksum(length, ver, seq, data_mv)

    # 总长度 = length + 3 （HEAD + LEN字段 + TAIL）
    buf = bytearray(length + 3)

    buf[0] = FRAME_HEAD
    buf[1] = u8(length)
    buf[2] = u8(ver)
    buf[3] = u8(seq)
    buf[4] = u8(chk)
    # 拷贝 DATA（逐字节）
    if data_len:
        buf[5:5 + data_len] = data_mv
    buf[-1] = FRAME_TAIL
    return bytes(buf)


def parse_frame_data(frame: BytesLike) -> bytes:
    """
    从完整帧中解析出 DATA 字段
    :param frame: 完整帧（bytes-like）
    :return: DATA 字段（bytes），如帧格式不合法则抛出 ValueError
    """
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise TypeError("frame must be bytes-like")

    mv = _as_byte_view(frame)
    total_len = len(mv)

    # 最小帧：LEN=3（无 DATA），总长 = 3 + 3 = 6
    if total_len < 6:
        raise ValueError("frame too short")
    if mv[0] != FRAME_HEAD or mv[-1] != FRAME_TAIL:
        raise ValueError("invalid frame head or tail")

    length = int(mv[1])  # LEN 域
    if length < 3:
        raise ValueError("invalid LEN (<3)")

    expected_len = length + 3  # HEAD(1) + LEN(1) + LEN段(length) + TAIL(1)
    if total_len != expected_len:
        raise ValueError(f"frame length mismatch: expected {expected_len}, got {total_len}")

    ver, seq, chk = mv[2], mv[3], mv[4]
    data_mv = mv[5:-1]  # 逐字节视图切片

    if chk != checksum(length, ver, seq, data_mv):
        raise ValueError("checksum error")

    return data_mv.tobytes()
