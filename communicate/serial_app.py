# serial_app.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import threading
from typing import Optional, Iterable, Tuple, Union

from .serial import SyncSerial, SerialConfig
from serial.tools import list_ports
from core.config import save_config, load_config
from core.paths import SERIAL_CONFIG_PATH
from core.logger import logger

# 协议编解码器（类版本）
from .protocol import FrameCodec, DataCodec
from .protocol.protocol_py.protocol_defs import Var, Msg  # 如无需要可移除

# ----------------------------------------------------------------------
# 全局对象与“最近一帧”缓存（线程安全）
# ----------------------------------------------------------------------
_serial: SyncSerial = SyncSerial()
_ports = []

_frame_codec = FrameCodec()   # 负责帧层：build / feed / parse
_data_codec = DataCodec()     # 负责 DATA(TLV) 层：encode/decode

_latest_received_frame_bytes: bytes = b""   # 最近一帧的“完整帧”（AA ... 55）
_latest_frame_data_bytes: bytes = b""       # 最近一帧的 DATA 字段（可能为 b''）
_latest_frame_decoded = None                # 最近一帧 DATA 的解码结果（DataPacket 或 None）

_frame_lock = threading.Lock()              # 并发访问保护


# ==============================
# 基本串口管理（同步）
# ==============================
def get_serial() -> SyncSerial:
    return _serial


def scan_serial_ports():
    global _ports
    _ports = list_ports.comports()
    return _ports


def ports_list():
    return _ports


def init_serial(port: Optional[str] = None) -> SyncSerial:
    """初始化串口并注册接收回调。"""
    scan_serial_ports()
    config = load_config(SERIAL_CONFIG_PATH, SerialConfig)
    if config is None:
        if port is None:
            logger.warning("[Serial] 未找到串口配置，使用默认配置")
        config = SerialConfig()
    if port is not None:
        config.port = port
    if config.port and config.port not in [p.device for p in _ports]:
        logger.warning(f"[Serial] 你指定的串口 {config.port} 不在当前可用列表中")

    global _serial
    _serial = SyncSerial(config)
    _serial.set_recv_callback(_receive_callback)

    logger.info(f"[Serial] 初始化串口: {config.port} @ {config.baudrate}")
    return _serial


def select_serial_port(port: str):
    global _serial
    if port:
        _serial.cfg.port = port
        logger.info(f"[Serial] 已选择串口: {port}")
    else:
        logger.warning("[Serial] 未选择串口")


def start_serial() -> bool:
    """打开串口并启动后台接收线程。"""
    ok = _serial.open()
    if not ok:
        return False
    _serial.start_receiving()
    return True


def stop_serial():
    """停止后台接收并关闭串口。"""
    _serial.stop_receiving()
    _serial.close()


def save_serial_config():
    save_config(SERIAL_CONFIG_PATH, _serial.get_config())


# ==============================
# 接收：同步回调（后台线程中被调用）
# ==============================
def _receive_callback(data: bytes) -> None:
    """
    注册给 SyncSerial 的同步回调。
    在后台接收线程内被调用：帧层流式解析 → 取最后一帧 → 拆 DATA → 解码。
    """
    if not data:
        return
    try:
        frames = _frame_codec.feed(data)  # 可能解析出 0..N 帧
        if not frames:
            return

        last_frame = frames[-1]
        # parse() 返回 (ver, seq, data_bytes)
        _, _, data_bytes = _frame_codec.parse(last_frame)

        if len(data_bytes) == 0:
            decoded = None
        else:
            decoded = _data_codec.decode(data_bytes)

        with _frame_lock:
            global _latest_received_frame_bytes, _latest_frame_data_bytes, _latest_frame_decoded
            _latest_received_frame_bytes = last_frame
            _latest_frame_data_bytes = data_bytes
            _latest_frame_decoded = decoded

    except Exception as e:
        # 不让异常冒泡影响串口读线程
        logger.warning(f"[Serial] 处理接收数据失败: {e}")


# ==============================
# 发送：帧层封装后经串口同步发送
# ==============================
def send_data_bytes(data_bytes: bytes, *, seq: int | None = None) -> None:
    """
    直接发送已编码好的 DATA（这里只负责帧层封装）。
    """
    frame = _frame_codec.build(data_bytes, seq=seq)
    _serial.send(frame)


def send_tlvs(tlvs: Iterable[Tuple[int, bytes]], *,
              msg: Union[int, "Msg", None] = None,
              ver: int | None = None,
              seq: int | None = None) -> None:
    """
    发送 TLV 列表：tlvs = [(T, Vbytes), ...]
    - msg/ver 不传时使用 DataCodec 的默认值（通常 Msg.PC_TO_MCU / PROTOCOL_DATA_VER）
    """
    data_bytes = _data_codec.encode(tlvs, msg=msg, ver=ver)
    send_data_bytes(data_bytes, seq=seq)


def send_kv(kv: dict, *,
            msg: Union[int, "Msg", None] = None,
            ver: int | None = None,
            seq: int | None = None) -> None:
    """
    发送 {变量: Python值}（TLV-Data）。
    - 固定宽度变量（在 VAR_FIXED_SIZE 中声明）可直接填 int/bool/float/bytes
    - 可变长变量必须传 bytes-like
    """
    data_bytes = _data_codec.encode_kv(kv, msg=msg, ver=ver)
    send_data_bytes(data_bytes, seq=seq)


# ==============================
# 查询最近一帧（同步）
# ==============================
def get_latest_frame() -> Tuple[bytes, bytes, object | None]:
    """
    返回最近一次接收到的三元组：(完整帧 bytes, DATA 字节串, DATA 解码结果或 None)。
    使用锁保证读取一致性。
    """
    with _frame_lock:
        return _latest_received_frame_bytes, _latest_frame_data_bytes, _latest_frame_decoded


def reset_latest():
    """清空“最近一帧”缓存（测试或复位时可用）。"""
    global _latest_received_frame_bytes, _latest_frame_data_bytes, _latest_frame_decoded
    with _frame_lock:
        _latest_received_frame_bytes = b""
        _latest_frame_data_bytes = b""
        _latest_frame_decoded = None
