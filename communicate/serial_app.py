# serial_app.py
# -*- coding: utf-8 -*-
import asyncio
from typing import Optional, Iterable, Tuple, Union

from .serial import AsyncSerial, SerialConfig
from serial.tools import list_ports
from core.config import SERIAL_CONFIG_PATH, save_config, load_config
from core.logger import logger

# 协议编解码器（类版本）
from .protocol import FrameCodec, DataCodec  # 确保你把类暴露在 .protocol 包里
# 如果 DataCodec 的 Var/Msg/类型需要用到，也可以按需导入：
from .protocol.protocol_py.protocol_defs import Var, Msg

# ----------------------------------------------------------------------
# 全局对象与最近一次接收结果（注意：如果你不喜欢全局，可改成单例类封装）
# ----------------------------------------------------------------------
_serial: AsyncSerial = AsyncSerial()
_ports = []

_frame_codec = FrameCodec()   # 负责帧层：build / feed / parse
_data_codec = DataCodec()     # 负责 DATA(TLV) 层：encode/decode

_latest_received_frame_bytes: bytes = b""     # 最近一帧的“完整帧”（AA ... 55）
_latest_frame_data_bytes: bytes = b""         # 最近一帧的 DATA 字段（可能为 b''）
_latest_frame_decoded = None                  # 最近一帧 DATA 的解码结果（DataPacket 或 None）

_frame_lock = asyncio.Lock()  # 并发访问保护（回调中更新这些“最新值”）


# ==============================
# 基本串口管理
# ==============================
def get_serial() -> AsyncSerial:
    return _serial


def scan_serial_ports():
    global _ports
    _ports = list_ports.comports()
    return _ports


def ports_list():
    return _ports


def init_serial(port: Optional[str] = None) -> AsyncSerial:
    """初始化串口并注册同步回调（内部派发到异步处理）。"""
    scan_serial_ports()
    config = load_config(SERIAL_CONFIG_PATH, SerialConfig)
    if config is None:
        if port is None:
            logger.warning("[Serial] 未找到串口配置，使用默认配置")
        config = SerialConfig()
    if port is not None:
        config.port = port
    if config.port not in [p.device for p in _ports]:
        logger.warning(f"[Serial] 你指定的串口 {config.port} 不可用")

    global _serial
    _serial = AsyncSerial(config)

    # 注意：set_recv_callback 的签名要求同步函数
    _serial.set_recv_callback(_receive_callback)

    logger.info(f"[Serial] 初始化串口: {_serial.port}")
    return _serial


def select_serial_port(port: str):
    global _serial
    if port:
        _serial.port = port
        logger.info(f"[Serial] 已选择串口: {port}")
    else:
        logger.warning("[Serial] 未选择串口")


async def start_serial():
    global _serial
    await _serial.open()
    _serial.start_receiving()


async def stop_serial():
    global _serial
    await _serial.stop_receiving()
    await _serial.close()


def save_serial_config():
    global _serial
    save_config(SERIAL_CONFIG_PATH, _serial.get_config())


# ==============================
# 接收：同步回调 → 异步处理
# ==============================
def _receive_callback(data: bytes) -> None:
    """
    注册给 AsyncSerial 的同步回调。
    只负责把真正的异步处理派发到事件循环。
    """
    if not data:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    loop.create_task(_process_received(data))


async def _process_received(data: bytes) -> None:
    """
    真正的异步处理：帧层流式解析 → 取最后一帧 → 拆出 DATA → （可选）DATA 层解码
    """
    global _latest_received_frame_bytes, _latest_frame_data_bytes, _latest_frame_decoded

    try:
        frames = _frame_codec.feed(data)  # 可能解析出 0..N 帧
        if not frames:
            return

        # 这里保持与原逻辑一致：只记录“最后一帧”作为“最新”
        last_frame = frames[-1]

        # 拆出 (ver, seq, data_bytes)
        _, _, data_bytes = _frame_codec.parse(last_frame)

        # DATA 为空时不调用数据层解码（DataDecoder.decode 需要至少2字节 MSG|VER）
        if len(data_bytes) == 0:
            decoded = None
        else:
            decoded = _data_codec.decode(data_bytes)

        async with _frame_lock:
            _latest_received_frame_bytes = last_frame
            _latest_frame_data_bytes = data_bytes
            _latest_frame_decoded = decoded

    except Exception as e:
        # 不要让异常冒泡到串口底层；改用 warning 以免刷屏
        logger.warning(f"[Serial] 处理接收数据失败: {e}")


# ==============================
# 发送：若你只想发 DATA(TLV) 或 KV，这里提供便捷方法
# ==============================
async def send_data_bytes(data_bytes: bytes, *, seq: int | None = None) -> None:
    """
    直接发送已编码好的 DATA（注意：这里只负责帧层封装）。
    """
    frame = _frame_codec.build(data_bytes, seq=seq)
    await _serial.send(frame)


async def send_tlvs(tlvs: Iterable[Tuple[int, bytes]], *, msg: Union[int, "Msg", None] = None,
                    ver: int | None = None, seq: int | None = None) -> None:
    """
    发送 TLV 列表：tlvs = [(T, Vbytes), ...]
    - msg/ver 不传时，使用 DataCodec 的默认值（通常 Msg.PC_TO_MCU / PROTOCOL_DATA_VER）
    """
    data_bytes = _data_codec.encode(tlvs, msg=msg, ver=ver)
    await send_data_bytes(data_bytes, seq=seq)


async def send_kv(kv: dict, *, msg: Union[int, "Msg", None] = None,
                  ver: int | None = None, seq: int | None = None) -> None:
    """
    发送 {变量: Python值}。
    - 固定宽度变量（在 VAR_FIXED_SIZE 中声明）可直接填写 int/bool/bytes（bytes 长度需匹配）
    - 可变长变量必须传 bytes-like
    """
    data_bytes = _data_codec.encode_kv(kv, msg=msg, ver=ver)
    await send_data_bytes(data_bytes, seq=seq)


# ==============================
# 查询最近一帧
# ==============================
async def get_latest_frame() -> Tuple[bytes, bytes, object | None]:
    """
    返回最近一次接收到的三元组：(完整帧 bytes, DATA 字节串, DATA 解码结果或 None)。
    使用锁保证读取一致性。
    """
    async with _frame_lock:
        return _latest_received_frame_bytes, _latest_frame_data_bytes, _latest_frame_decoded


def reset_latest():
    """清空“最近一帧”缓存（测试或复位时可用）。"""
    global _latest_received_frame_bytes, _latest_frame_data_bytes, _latest_frame_decoded
    _latest_received_frame_bytes = b""
    _latest_frame_data_bytes = b""
    _latest_frame_decoded = None
