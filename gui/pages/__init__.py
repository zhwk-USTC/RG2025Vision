"""
页面模块包，包含应用中的各页面布局和逻辑
"""
from .main_page import render_main_page
from .about_page import render_about_page
from .config_page import render_config_page
from .sysinfo_page import render_sysinfo_page
from .debug_page import render_debug_page

__all__ = [
    'render_main_page',
    'render_about_page', 
    'render_config_page',
    'render_sysinfo_page',
    'render_debug_page'
    ]