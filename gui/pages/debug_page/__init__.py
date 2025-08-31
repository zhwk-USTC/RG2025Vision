from nicegui import ui
from .camera_debug_tab import render_camera_tab

def render_debug_page():
    with ui.tabs() as tabs:
        tab1 = ui.tab('摄像头及检测调试')
        tab2 = ui.tab('页面二')

    # 定义对应的标签内容
    with ui.tab_panels(tabs, value=tab1):
        with ui.tab_panel(tab1):
            render_camera_tab()
        with ui.tab_panel(tab2):
            ui.label('这是第二个页面的内容')