import threading
import asyncio
import time

from gui.gui_app import launch as gui_launch
from communicate.uart import run_uart
from vision.vision_app import run_vision
from core.logger import logger

def main():
    t_uart = threading.Thread(target=run_uart, daemon=True)
    t_vision = threading.Thread(target=run_vision, daemon=True)
    # t_uart.start()
    t_vision.start()

    logger.debug("所有子线程已启动，启动GUI...", notify_gui=False)
    try:
        gui_launch()
    except KeyboardInterrupt:
        logger.info('主进程退出', notify_gui=False)

if __name__ in {"__main__", "__mp_main__"}:
    main()
