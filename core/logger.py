import logging
import os
from datetime import datetime
from nicegui import ui

CONSOLE_LOG_LEVEL = logging.INFO
FILE_LOG_LEVEL = logging.WARNING
UI_LOG_LEVEL = logging.DEBUG

# 模块初始化：确保日志目录存在
LOG_DIR = os.path.join(os.path.dirname(__file__), '../.log')
os.makedirs(LOG_DIR, exist_ok=True)

class Logger:
    def __init__(self, name='app',
                 console_level=logging.INFO,
                 file_level=logging.INFO,
                 ui_level=logging.INFO,
                 logfile=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # 主logger最低，交给handler控制
        fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

        # 控制台
        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(console_level)
        self.console_handler.setFormatter(fmt)
        self.logger.addHandler(self.console_handler)

        # 文件 - 如果没有指定logfile，使用运行时间生成文件名
        if logfile is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            logfile = os.path.join(LOG_DIR, f'app_{timestamp}.log')
        
        self.file_handler = logging.FileHandler(logfile, encoding='utf-8')
        self.file_handler.setLevel(file_level)
        self.file_handler.setFormatter(fmt)
        self.logger.addHandler(self.file_handler)

        # UI日志级别
        self.ui_level = ui_level

    def debug(self, msg, *args, notify_gui=True, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
        if notify_gui and logging.DEBUG >= self.ui_level:
            ui.notify(str(msg), type='positive')

    def info(self, msg, *args, notify_gui=True, **kwargs):
        self.logger.info(msg, *args, **kwargs)
        if notify_gui and logging.INFO >= self.ui_level:
            ui.notify(str(msg), type='info')

    def warning(self, msg, *args, notify_gui=True, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
        if notify_gui and logging.WARNING >= self.ui_level:
            ui.notify(str(msg), type='warning')

    def error(self, msg, *args, notify_gui=True, **kwargs):
        self.logger.error(msg, *args, **kwargs)
        if notify_gui and logging.ERROR >= self.ui_level:
            ui.notify(str(msg), type='negative')

# 单例
logger = Logger(console_level=CONSOLE_LOG_LEVEL,
                file_level=FILE_LOG_LEVEL,
                ui_level=UI_LOG_LEVEL)
