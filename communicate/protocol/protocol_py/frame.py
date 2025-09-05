# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Union, List, Tuple, Optional

# ----------------- 公共类型与常量 -----------------
BytesLike = Union[bytes, bytearray, memoryview]

FRAME_HEAD = 0xAA
FRAME_TAIL = 0x55
VERSION    = 0x00

# LEN 为 1 字节；LEN = 3 + N（VER+SEQ+CHK+DATA）
MAX_DATA_LEN = 0xFF - 3       # 252
MAX_FRAME_TOTAL_LEN = 0xFF + 3  # = 255 + 3 = 258
MIN_FRAME_TOTAL_LEN = 6         # LEN=3 → 总长=6

# ----------------- 工具函数（内部复用） -----------------
def u8(x: int) -> int:
    return x & 0xFF

def _as_byte_view(b: BytesLike) -> memoryview:
    mv = memoryview(b)
    try:
        return mv.cast('B')
    except TypeError:
        return memoryview(bytes(b))

def _sum_bytes(data: BytesLike) -> int:
    return sum(_as_byte_view(data))

def _checksum(len_byte: int, ver: int, seq: int, data: BytesLike) -> int:
    s = u8(len_byte) + u8(ver) + u8(seq) + _sum_bytes(data)
    return u8(s)

# =========================================================
# 编码器：负责构帧（可选自动递增 SEQ）
# =========================================================
class FrameEncoder:
    """
    负责编码（build frame）。
    - ver: 协议版本（默认 0x00）
    - auto_seq: 是否自动维护 SEQ（默认 True）
    - init_seq: 初始 seq 值（默认 0）
    """
    __slots__ = ("ver", "auto_seq", "_seq")

    def __init__(self, ver: int = VERSION, *, auto_seq: bool = True, init_seq: int = 0) -> None:
        self.ver = u8(ver)
        self.auto_seq = auto_seq
        self._seq = u8(init_seq)

    @property
    def seq(self) -> int:
        return self._seq

    def reset_seq(self, value: int = 0) -> None:
        self._seq = u8(value)

    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) & 0xFF
        return self._seq

    def build(self, data: BytesLike = b"", *, seq: Optional[int] = None) -> bytes:
        """
        构建一帧：AA LEN VER SEQ CHK DATA... 55
        如果未显式提供 seq 且 auto_seq=True，则自动递增。
        """
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes-like")

        data_mv = _as_byte_view(data)
        data_len = len(data_mv)
        if data_len > MAX_DATA_LEN:
            raise ValueError(f"data too long: {data_len} > {MAX_DATA_LEN}")

        if seq is None:
            seq_val = self._next_seq() if self.auto_seq else self._seq
        else:
            seq_val = u8(seq)
            if self.auto_seq:
                # 与自动 seq 并不冲突：允许覆盖一次
                self._seq = seq_val

        length = 3 + data_len  # VER + SEQ + CHK + DATA
        chk = _checksum(length, self.ver, seq_val, data_mv)

        buf = bytearray(length + 3)  # HEAD + LEN段(length) + TAIL
        buf[0] = FRAME_HEAD
        buf[1] = u8(length)
        buf[2] = self.ver
        buf[3] = u8(seq_val)
        buf[4] = u8(chk)
        if data_len:
            buf[5:5 + data_len] = data_mv
        buf[-1] = FRAME_TAIL
        return bytes(buf)

# =========================================================
# 解码器/流式解析器：喂增量字节 → 产出完整帧
# =========================================================
class FrameDecoder:
    """
    串口/Socket 等“流式”输入解析器：
      - feed(bytes) -> List[bytes]: 解析出0..N个完整帧（原始帧字节）
      - parse_frame_data(frame) -> (ver, seq, data_bytes)
    具备自恢复：遇到坏帧会丢弃当前“帧头”，同步到下一个 0xAA。
    """
    __slots__ = ("_buf", "max_buffer")

    def __init__(self, *, max_buffer: int = 4096) -> None:
        self._buf = bytearray()
        self.max_buffer = max_buffer

    def clear(self) -> None:
        self._buf.clear()

    # ----------- 高层 API -----------
    def feed(self, data: BytesLike) -> List[bytes]:
        """喂入新收到的字节，返回解析出的完整帧（每项为 bytes）。"""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes-like")
        self._buf += _as_byte_view(data)

        if len(self._buf) > self.max_buffer:
            del self._buf[: len(self._buf) - self.max_buffer]

        frames: List[bytes] = []
        while True:
            f = self._try_extract_one_frame()
            if f is None:
                break
            frames.append(f)
        return frames

    def iter_frames(self, data: BytesLike):
        for f in self.feed(data):
            yield f

    @staticmethod
    def parse_frame_data(frame: BytesLike) -> Tuple[int, int, bytes]:
        """
        校验并解析“完整帧”，返回 (ver, seq, data_bytes)。
        """
        if not isinstance(frame, (bytes, bytearray, memoryview)):
            raise TypeError("frame must be bytes-like")

        mv = _as_byte_view(frame)
        total_len = len(mv)

        if total_len < MIN_FRAME_TOTAL_LEN:
            raise ValueError("frame too short")
        if mv[0] != FRAME_HEAD or mv[-1] != FRAME_TAIL:
            raise ValueError("invalid frame head or tail")

        length = int(mv[1])
        if length < 3:
            raise ValueError("invalid LEN (<3)")

        expected_len = length + 3
        if total_len != expected_len:
            raise ValueError(f"frame length mismatch: expected {expected_len}, got {total_len}")

        ver, seq, chk = mv[2], mv[3], mv[4]
        data_mv = mv[5:-1]

        if chk != _checksum(length, ver, seq, data_mv):
            raise ValueError("checksum error")

        return int(ver), int(seq), data_mv.tobytes()

    # ----------- 内部实现 -----------
    def _resync_to_next_head(self) -> bool:
        try:
            idx = self._buf.index(FRAME_HEAD)
        except ValueError:
            self._buf.clear()
            return False
        if idx > 0:
            del self._buf[:idx]
        return True

    def _try_extract_one_frame(self) -> Optional[bytes]:
        if not self._buf:
            return None
        if self._buf[0] != FRAME_HEAD:
            if not self._resync_to_next_head():
                return None

        if len(self._buf) < 2:
            return None
        length = int(self._buf[1])
        if length < 3:
            del self._buf[0]
            return self._try_extract_one_frame()

        expected_total = length + 3
        if expected_total < MIN_FRAME_TOTAL_LEN or expected_total > MAX_FRAME_TOTAL_LEN:
            del self._buf[0]
            return self._try_extract_one_frame()

        if len(self._buf) < expected_total:
            return None

        candidate = self._buf[:expected_total]
        if candidate[-1] != FRAME_TAIL:
            del self._buf[0]
            return self._try_extract_one_frame()

        ver = candidate[2]
        seq = candidate[3]
        chk = candidate[4]
        data_mv = memoryview(candidate)[5:-1]
        if chk != _checksum(length, ver, seq, data_mv):
            del self._buf[0]
            return self._try_extract_one_frame()

        del self._buf[:expected_total]
        return bytes(candidate)

# =========================================================
# 可选门面：统一入口（组合编码+解码）
# =========================================================
class FrameCodec:
    """
    组合式门面：对外暴露 build / feed / parse 三个常用操作。
    """
    __slots__ = ("enc", "dec")

    def __init__(self, *, ver: int = VERSION, auto_seq: bool = True, init_seq: int = 0, max_buffer: int = 4096):
        self.enc = FrameEncoder(ver=ver, auto_seq=auto_seq, init_seq=init_seq)
        self.dec = FrameDecoder(max_buffer=max_buffer)

    def build(self, data: BytesLike = b"", *, seq: Optional[int] = None) -> bytes:
        return self.enc.build(data, seq=seq)

    def feed(self, data: BytesLike) -> List[bytes]:
        return self.dec.feed(data)

    def parse(self, frame: BytesLike) -> Tuple[int, int, bytes]:
        return self.dec.parse_frame_data(frame)
