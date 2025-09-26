# core/logger.py
import logging
import os
from datetime import datetime
from typing import Optional, Callable

from nicegui import ui

CONSOLE_LOG_LEVEL = logging.DEBUG
FILE_LOG_LEVEL = logging.WARNING
UI_LOG_LEVEL = logging.DEBUG

LOG_DIR = os.path.join(os.path.dirname(__file__), '../.log')
os.makedirs(LOG_DIR, exist_ok=True)

# 控制台/文件使用的详细格式（含时间/等级/模块名）
_FMT = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
# UI 使用的极简格式（仅消息体）
_UI_FMT = logging.Formatter('%(message)s')


class UiHandler(logging.Handler):
    """
    将日志推送到 NiceGUI notify。
    为了在后台任务中也能安全弹窗，这里支持注入 container_getter：
      - 若提供了容器，则在 `with container:` 中调用 ui.notify（避免 slot 报错）
      - 若没有容器，仍尝试直接 ui.notify（可能在某些后台场景失败，但已被 try/except 兜底）
    """
    def __init__(self, container_getter: Optional[Callable[[], Optional[ui.element]]] = None):
        super().__init__()
        self._container_getter = container_getter
        # 默认给 UI 设置极简格式
        self.setFormatter(_UI_FMT)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)  # 使用 _UI_FMT，仅 message
            notify_type = (
                'negative' if record.levelno >= logging.ERROR else
                'warning'  if record.levelno >= logging.WARNING else
                'info'     if record.levelno >= logging.INFO else
                'positive'
            )

            container = self._container_getter() if callable(self._container_getter) else None
            if container is not None:
                # 在指定容器上下文中创建 UI，适配后台任务
                try:
                    with container:
                        ui.notify(msg, type=notify_type)
                    return
                except Exception:
                    # 容器失败则回退到直接 notify
                    pass

            # 无容器或进入容器失败，尽力直接弹窗（若在后台可能失败，已被外层 try 捕获）
            ui.notify(msg, type=notify_type)
        except Exception:
            # 任何 UI 异常都不影响其他 handler 的正常工作
            pass


class Logger:
    def __init__(self, name: str = 'app',
                 console_level: int = logging.INFO,
                 file_level: int = logging.INFO,
                 ui_level: int = logging.INFO,
                 logfile: Optional[str] = None):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)

        # 控制台 handler（只添加一次）
        if not any(isinstance(h, logging.StreamHandler) for h in self._logger.handlers):
            ch = logging.StreamHandler()
            ch.setLevel(console_level)
            ch.setFormatter(_FMT)
            self._logger.addHandler(ch)

        # 用于后台任务 UI 安全通知的容器引用（由 set_ui_target 设置）
        self._ui_container: Optional[ui.element] = None

        # UI handler（只添加一次），通过回调拿容器；使用简洁格式 _UI_FMT
        if not any(isinstance(h, UiHandler) for h in self._logger.handlers):
            uh = UiHandler(container_getter=lambda: self._ui_container)
            uh.setLevel(ui_level)
            # 确保万一被外部修改，这里强制一次极简格式
            uh.setFormatter(_UI_FMT)
            self._logger.addHandler(uh)

        self._file_level = file_level
        self._logfile_path = logfile
        self._file_handler: Optional[logging.FileHandler] = None

    # ---------- UI 容器设置 ----------
    def set_ui_target(self, container: ui.element) -> None:
        """
        指定一个 NiceGUI 容器作为 UI 通知的“目标槽位”。
        这样在后台任务里也能安全弹出 notify，而不会出现 “slot stack is empty”。
        """
        self._ui_container = container

    # ---------- 文件日志 ----------
    def _ensure_file_handler(self) -> None:
        if self._file_handler:
            return
        if not self._logfile_path:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            self._logfile_path = os.path.join(LOG_DIR, f'app_{ts}.log')
        try:
            fh = logging.FileHandler(self._logfile_path, encoding='utf-8')
            fh.setLevel(self._file_level)
            fh.setFormatter(_FMT)
            self._logger.addHandler(fh)
            self._file_handler = fh
        except Exception as e:
            # 失败也要在控制台可见
            self._logger.error(f'无法创建日志文件 {self._logfile_path}: {e}')

    def enable_file(self, logfile: Optional[str] = None) -> None:
        if logfile:
            self._logfile_path = logfile
        self._ensure_file_handler()

    # ---------- 统一记录入口 ----------
    def _log(self, level: int, msg, *args, **kwargs) -> None:
        if level >= self._file_level and self._file_handler is None:
            self._ensure_file_handler()
        self._logger.log(level, msg, *args, **kwargs)

    # ---------- 常用方法 ----------
    def debug(self, msg, *args, **kwargs):   self._log(logging.DEBUG, msg, *args, **kwargs)
    def info(self, msg, *args, **kwargs):    self._log(logging.INFO, msg, *args, **kwargs)
    def warning(self, msg, *args, **kwargs): self._log(logging.WARNING, msg, *args, **kwargs)
    def error(self, msg, *args, **kwargs):   self._log(logging.ERROR, msg, *args, **kwargs)


# 单例
logger = Logger(
    console_level=CONSOLE_LOG_LEVEL,
    file_level=FILE_LOG_LEVEL,
    ui_level=UI_LOG_LEVEL,
)
