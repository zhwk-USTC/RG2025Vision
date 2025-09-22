import asyncio
from nicegui import ui, app
from typing import Optional, Callable, Awaitable
from .pages import *
from core.logger import logger

def render_nav_drawer():
    with ui.left_drawer().classes('bg-grey-2').style('min-width:120px;max-width:240px;width:auto;'):
        ui.label('RoboGame 2025').classes('text-h5 q-mt-md q-mb-lg')
        with ui.list():
            with ui.item(on_click=lambda: ui.navigate.to('/')).classes('q-hoverable q-pa-md'):
                ui.icon('home')
                ui.item_section('主页面')
            # with ui.item(on_click=lambda: ui.navigate.to('/classic')).classes('q-hoverable q-pa-md'):
            #     ui.icon('view_classic')
            #     ui.item_section('经典版')
            with ui.item(on_click=lambda: ui.navigate.to('/debug')).classes('q-hoverable q-pa-md'):
                ui.icon('build')
                ui.item_section('调试')
            with ui.item(on_click=lambda: ui.navigate.to('/config')).classes('q-hoverable q-pa-md'):
                ui.icon('settings')
                ui.item_section('配置')
            # with ui.item(on_click=lambda: ui.navigate.to('/sysinfo')).classes('q-hoverable q-pa-md'):
            #     ui.icon('memory')
            #     ui.item_section('系统信息')
            # with ui.item(on_click=lambda: ui.navigate.to('/about')).classes('q-hoverable q-pa-md'):
            #     ui.icon('info')
            #     ui.item_section('关于')

@ui.page('/')
def main_page():
    render_nav_drawer()
    render_main_page()

@ui.page('/debug')
def debug_page():
    render_nav_drawer()
    render_debug_page()
    
@ui.page('/config')
def config_page():
    render_nav_drawer()
    render_config_page()

@ui.page('/sysinfo')
def sysinfo_page():
    render_nav_drawer()
    render_sysinfo_page()

@ui.page('/about')
def about_page():
    render_nav_drawer()
    render_about_page()

def launch(
    *,
    host: str = '0.0.0.0',
    port: int = 8080,
    show: bool = False,
    on_startup: Optional[Callable[[], Awaitable[None]]] = None,
    on_shutdown: Optional[Callable[[], Awaitable[None]]] = None,
) -> None:
    # 注册生命周期回调（支持 async 或 sync 函数）
    if on_startup:
        app.on_startup(on_startup)
        logger.info('已注册 on_startup 回调')
    if on_shutdown:
        app.on_shutdown(on_shutdown)
        logger.info('已注册 on_shutdown 回调')

    logger.info(f'启动 NiceGUI (host={host}, port={port}, show={show})')
    ui.run(host=host, port=port, show=show)