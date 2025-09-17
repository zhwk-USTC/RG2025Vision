from nicegui import ui

from .camera_config_tab import render_camera_config_tab
from .detection_config_tab import render_detection_config_tab
from .localization_config_tab import render_localization_tab
from .serial_config_tab import render_serial_config_tab
from .field_config_tab import render_field_config_tab
from gui.utils.tab_memory import create_memorable_tabs

def render_config_page():
    """渲染配置页面，支持Tab记忆功能"""
    # Tab配置映射
    tab_configs = {
        'camera': ('摄像头配置', render_camera_config_tab),
        'detection': ('检测配置', render_detection_config_tab),
        'serial': ('串口配置', render_serial_config_tab),
        'field': ('场地配置', render_field_config_tab)
    }
    
    # 使用通用Tab记忆功能
    create_memorable_tabs('config_page_last_tab', tab_configs, 'camera')