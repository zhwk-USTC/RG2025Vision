from nicegui import ui

from .camera_config_tab import render_camera_config_tab
from .detection_config_tab import render_detection_config_tab
from .localization_config_tab import render_localization_tab
from .serial_config_tab import render_serial_config_tab

def render_config_page():
    with ui.tabs() as tabs:
        tab1 = ui.tab('摄像头配置')
        tab2 = ui.tab('检测配置')
        tab3 = ui.tab('串口配置')
        tab4 = ui.tab('定位配置')

    # 定义对应的标签内容
    with ui.tab_panels(tabs, value=tab1):
        with ui.tab_panel(tab1):
            render_camera_config_tab()
        with ui.tab_panel(tab2):
            render_detection_config_tab()
        with ui.tab_panel(tab3):
            render_serial_config_tab()
        with ui.tab_panel(tab4):
            render_localization_tab()