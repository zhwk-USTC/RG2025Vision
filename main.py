# main.py
import asyncio
from typing import Optional

from core.logger import logger
from gui import launch as gui_launch
from nicegui import app,background_tasks
from communicate.serial_app import init_serial, start_serial, stop_serial
from vision.runtime import init_vision, get_vision, reset_vision

async def on_gui_startup():
    vs = init_vision()
    serial = init_serial()
async def on_gui_shutdown():
    reset_vision()
    stop_serial()

def main():
    """主程序入口"""
    logger.info("准备启动程序 ...")
    try:
        gui_launch(on_startup=on_gui_startup, on_shutdown=on_gui_shutdown)
    except KeyboardInterrupt:
        logger.info("主进程收到 Ctrl+C")


if __name__ in {"__main__", "__mp_main__"}:
    main()
