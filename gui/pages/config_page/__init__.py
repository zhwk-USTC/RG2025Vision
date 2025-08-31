from nicegui import ui

from .camera_config_tab import render_camera_config_tab

def render_config_page():
    with ui.tabs() as tabs:
        tab1 = ui.tab('摄像头及检测配置')

    # 定义对应的标签内容
    with ui.tab_panels(tabs, value=tab1):
        with ui.tab_panel(tab1):
            render_camera_config_tab()