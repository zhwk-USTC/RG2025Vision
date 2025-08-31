from nicegui import ui
import asyncio
from core.logger import logger


def render_main_page():
    ui.markdown("# RoboGame2025 控制界面\n欢迎使用小车控制系统！")

    def on_test_btn_click():
        logger.info("示例按钮被点击！")

    ui.button("示例按钮", on_click=on_test_btn_click)
    
