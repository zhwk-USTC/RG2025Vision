import asyncio
from nicegui import ui
import numpy as np
from .tabs.about_tab import render_about_tab
from .tabs.debug_tab import render_debug_tab
from .tabs.main_tab import render_main_tab
from .tabs.sysinfo_tab import render_sysinfo_tab
from .tabs.camera_tab import render_camera_tab
from .tabs.config_tab import render_config_tab


def render_nav_drawer():
    with ui.left_drawer().classes('bg-grey-2').style('min-width:120px;max-width:240px;width:auto;'):
        ui.label('RoboGame 2025').classes('text-h5 q-mt-md q-mb-lg')
        with ui.list():
            with ui.item(on_click=lambda: ui.navigate.to('/')).classes('q-hoverable q-pa-md'):
                ui.icon('home')
                ui.item_section('主页面')
            with ui.item(on_click=lambda: ui.navigate.to('/camera')).classes('q-hoverable q-pa-md'):
                ui.icon('photo_camera')
                ui.item_section('摄像头')
            with ui.item(on_click=lambda: ui.navigate.to('/debug')).classes('q-hoverable q-pa-md'):
                ui.icon('build')
                ui.item_section('调试')
            with ui.item(on_click=lambda: ui.navigate.to('/config')).classes('q-hoverable q-pa-md'):
                ui.icon('settings')
                ui.item_section('配置')
            with ui.item(on_click=lambda: ui.navigate.to('/sysinfo')).classes('q-hoverable q-pa-md'):
                ui.icon('memory')
                ui.item_section('系统信息')
            with ui.item(on_click=lambda: ui.navigate.to('/about')).classes('q-hoverable q-pa-md'):
                ui.icon('info')
                ui.item_section('关于')

@ui.page('/')
def main_page():
    render_nav_drawer()
    render_main_tab()

@ui.page('/camera')
def camera_page():
    render_nav_drawer()
    render_camera_tab()

@ui.page('/debug')
def debug_page():
    render_nav_drawer()
    render_debug_tab()
    
@ui.page('/config')
def config_page():
    render_nav_drawer()
    render_config_tab()

@ui.page('/sysinfo')
def sysinfo_page():
    render_nav_drawer()
    render_sysinfo_tab()

@ui.page('/about')
def about_page():
    render_nav_drawer()
    render_about_tab()

def launch():
    ui.run(host='0.0.0.0', port=8080, show=False)