import asyncio
import serial_asyncio
import contextlib
from typing import Optional, Callable, Union


class AsyncSerial:
    """
    纯字节流版：
    - 回调类型: Callable[[bytes], None]，每次回调一块原始 bytes
    - send 仅接受 bytes / bytearray / memoryview
    """
    def __init__(self, port: str = "", baudrate: int = 115200, chunk_size: int = 256):
        self.port = port
        self.baudrate = baudrate
        self.chunk_size = max(1, int(chunk_size))

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._callback: Optional[Callable[[bytes], None]] = None
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def open(self):
        try:
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self.port, baudrate=self.baudrate
            )
        except Exception as e:
            print(f"打开串口失败: {e}")

    def set_recv_callback(self, callback: Optional[Callable[[bytes], None]]):
        """设置接收回调：参数是 bytes（原始字节块）。"""
        self._callback = callback

    async def send(self, data: Union[bytes, bytearray, memoryview]):
        """发送原始字节；若传入非字节类型会抛出 TypeError。"""
        if not self._writer:
            raise RuntimeError("串口未打开，请先 await open()")
        if isinstance(data, (bytes, bytearray, memoryview)):
            self._writer.write(bytes(data))
            await self._writer.drain()
        else:
            raise TypeError("send() 仅接受 bytes/bytearray/memoryview")

    def start_receiving(self):
        """在事件循环内启动读任务（幂等）。"""
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._rx_loop(), name="AsyncSerialRecv")

    async def stop_receiving(self):
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=1.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                with contextlib.suppress(Exception):
                    await self._task

    async def close(self):
        await self.stop_receiving()
        if self._writer:
            transport = self._writer.transport
            if transport:
                transport.close()
            self._writer = None
            self._reader = None

    async def _rx_loop(self):
        try:
            while not self._stop.is_set():
                # 读取一块字节数据（默认 256），为空则小睡让出事件循环
                chunk = await self._reader.read(self.chunk_size)
                if not chunk:
                    await asyncio.sleep(0.005)
                    continue

                if self._callback:
                    try:
                        self._callback(chunk)  # 直接回调原始 bytes
                    except Exception:
                        # 不让用户回调异常中断循环
                        pass
        except asyncio.CancelledError:
            pass
        except Exception:
            # 轻量容错：不向外抛，避免杀掉事件循环
            await asyncio.sleep(0.05)
