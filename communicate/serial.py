from typing import Optional, Callable, Union
from dataclasses import dataclass
import threading
import time
import serial

@dataclass
class SerialConfig:
    port: str = ''
    baudrate: int = 115200
    chunk_size: int = 64  # 减小chunk_size，提高响应速度

class SyncSerial:
    """
    同步串口（基于 PySerial）
    - set_recv_callback(cb): 每次收到一块 bytes 就回调一次
    - start_receiving()/stop_receiving(): 以后台线程阻塞读取
    - send(data): 同步发送原始 bytes
    """
    def __init__(self, config: SerialConfig = SerialConfig()):
        self.cfg = config
        self._ser: Optional[serial.Serial] = None
        self._callback: Optional[Callable[[bytes], None]] = None

        self._rx_thread: Optional[threading.Thread] = None
        self._rx_stop_flag = threading.Event()

        # 保护串口对象的锁（写/关）
        self._lock = threading.Lock()

    # ---------- 打开/关闭 ----------
    def open(self) -> bool:
        """打开串口；返回是否成功。"""
        try:
            self._ser = serial.Serial(
                port=self.cfg.port,
                baudrate=self.cfg.baudrate,
                timeout=0.1,  # 设置读超时为100ms，避免无限阻塞
                write_timeout=1.0,  # 设置写超时为1秒
            )
            return True
        except Exception as e:
            print(f"[SyncSerial] 打开串口失败: {e}")
            self._ser = None
            return False

    def close(self) -> None:
        """停止接收线程并关闭串口。"""
        self.stop_receiving()
        with self._lock:
            if self._ser is not None:
                try:
                    self._ser.close()
                except Exception:
                    pass
                self._ser = None

    # ---------- 发送 ----------
    def send(self, data: Union[bytes, bytearray, memoryview]) -> None:
        """同步发送原始字节；仅接受 bytes/bytearray/memoryview。"""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("send() 仅接受 bytes/bytearray/memoryview")
        with self._lock:
            if self._ser is None or not self._ser.is_open:
                raise RuntimeError("串口未打开，请先调用 open()")
            self._ser.write(bytes(data))
            self._ser.flush()  # 可选：确保尽快刷出

    # ---------- 接收（回调） ----------
    def set_recv_callback(self, callback: Optional[Callable[[bytes], None]]) -> None:
        """设置接收回调：参数是 bytes（原始字节块）。"""
        self._callback = callback

    def start_receiving(self) -> None:
        """启动后台读取线程（幂等）。"""
        if self._rx_thread and self._rx_thread.is_alive():
            return
        if self._ser is None or not self._ser.is_open:
            raise RuntimeError("串口未打开，请先调用 open()")
        self._rx_stop_flag.clear()
        self._rx_thread = threading.Thread(target=self._rx_loop, name="SyncSerialRecv", daemon=True)
        self._rx_thread.start()

    def stop_receiving(self, timeout: float = 1.0) -> None:
        """请求停止接收线程并等待其退出。"""
        self._rx_stop_flag.set()
        th = self._rx_thread
        if th and th.is_alive():
            th.join(timeout=timeout)
        self._rx_thread = None

    # ---------- 工具 ----------
    def is_open(self) -> bool:
        return bool(self._ser and self._ser.is_open)

    def get_config(self) -> SerialConfig:
        return self.cfg

    # ---------- 内部线程函数 ----------
    def _rx_loop(self) -> None:
        chunk_size = max(1, int(self.cfg.chunk_size))
        while not self._rx_stop_flag.is_set():
            try:
                with self._lock:
                    ser = self._ser
                if ser is None or not ser.is_open:
                    time.sleep(0.01)  # 减少空等时间
                    continue

                # 阻塞式读（受 timeout 限制），尽量一次取 chunk_size
                data = ser.read(chunk_size)
                if not data:
                    # 超时无数据：短暂让出CPU，但不要太长
                    continue  # 直接继续，不需要sleep

                cb = self._callback
                if cb:
                    try:
                        cb(data)
                    except Exception:
                        # 不让用户回调异常杀掉线程
                        pass

            except Exception:
                # 轻量容错：短暂休眠再继续
                time.sleep(0.01)  # 减少错误恢复时间
                continue
