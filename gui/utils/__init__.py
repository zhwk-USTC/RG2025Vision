"""
GUI工具模块
包含各种GUI相关的辅助工具和组件
"""

from .tab_memory import TabMemoryManager, create_memorable_tabs
from .image_widgets import get_empty_img, prepare_image_for_display

__all__ = [
    'TabMemoryManager',
    'create_memorable_tabs', 
    'get_empty_img',
    'prepare_image_for_display',
]