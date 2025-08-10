import asyncio
from communicate.serial_manager import SerialManager
from typing import Optional
from pyee.asyncio import AsyncIOEventEmitter

# 假设事件总线由主程序传入

def get_uart_manager():
    # 串口端口和波特率可根据实际情况修改
    return SerialManager(port='COM3', baudrate=9600)

async def run_uart():
    pass
#     uart = get_uart_manager()
#     uart.start_receiving()
#     loop = asyncio.get_event_loop()
#     queue = asyncio.Queue()

#     def on_data(data):
#         # 串口收到数据时放入队列
#         loop.call_soon_threadsafe(queue.put_nowait, data)

#     uart.set_recv_callback(on_data)

#     while True:
#         data = await queue.get()
#         # if ee is not None:
#         #     ee.emit('uart_data', data)
#         # 这里也可以直接处理数据
#         await asyncio.sleep(0.01)
