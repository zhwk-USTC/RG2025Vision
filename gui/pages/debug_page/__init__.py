from nicegui import ui, app
from .camera_debug_tab import render_camera_debug_tab
from .detection_debug_tab import render_detection_debug_tab
from .localization_debug_tab import render_localization_tab
from .serial_debug_tab import render_serial_tab
from gui.utils.tab_memory import create_memorable_tabs

def render_debug_page():
    """渲染调试页面，支持Tab记忆功能"""
    # Tab配置映射
    tab_configs = {
        'camera': ('摄像头调试', render_camera_debug_tab),
        'detection': ('检测调试', render_detection_debug_tab),
        'serial': ('串口调试', render_serial_tab),
        'localization': ('定位调试', render_localization_tab)
    }
    
    # 使用通用Tab记忆功能
    create_memorable_tabs('debug_page_last_tab', tab_configs, 'camera')