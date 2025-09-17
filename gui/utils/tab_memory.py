#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的Tab记忆功能
仅在进程内记住上次访问的Tab，不使用持久化存储
"""

from typing import Dict, Callable, Tuple, Optional
from nicegui import ui

class SimpleTabMemory:
    """简单的Tab记忆管理器 - 仅进程内记忆"""
    
    # 类变量存储所有Tab状态
    _tab_states: Dict[str, str] = {}
    
    def __init__(self, memory_key: str, default_tab: Optional[str] = None):
        """
        初始化Tab记忆管理器
        
        Args:
            memory_key: 用于区分不同页面/组件的Tab状态的唯一标识
            default_tab: 默认选中的Tab键值
        """
        self.memory_key = memory_key
        self.default_tab = default_tab
        self._tabs: Optional[ui.tabs] = None
    
    def get_last_tab(self, available_tabs: list) -> str:
        """获取上次访问的Tab，如果不存在则返回默认值"""
        last_tab = self._tab_states.get(self.memory_key)
        if last_tab and last_tab in available_tabs:
            return last_tab
        return self.default_tab or (available_tabs[0] if available_tabs else '')
    
    def set_current_tab(self, tab_key: str):
        """设置当前Tab并记住状态"""
        self._tab_states[self.memory_key] = tab_key
        if self._tabs:
            self._tabs.value = tab_key
    
    def create_tabs_with_memory(self, tab_configs: Dict[str, Tuple[str, Callable]]) -> Tuple[ui.tabs, Dict[str, ui.tab]]:
        """
        创建带记忆功能的Tabs
        
        Args:
            tab_configs: Tab配置字典 {tab_key: (tab_label, content_function)}
        
        Returns:
            (tabs组件, tab对象字典)
        """
        available_tabs = list(tab_configs.keys())
        initial_tab = self.get_last_tab(available_tabs)
        
        # 如果是第一次访问（没有记忆的Tab），记住第一个Tab
        if self.memory_key not in self._tab_states and available_tabs:
            self._tab_states[self.memory_key] = initial_tab
        
        # 创建Tabs容器
        with ui.tabs() as tabs:
            tab_objects = {}
            for tab_key, (tab_label, _) in tab_configs.items():
                tab_objects[tab_key] = ui.tab(tab_key, label=tab_label)
        
        self._tabs = tabs
        
        # 监听Tab切换事件
        def on_tab_change():
            # 直接获取当前选中的Tab值
            current_value = tabs.value
            if current_value:
                self.set_current_tab(current_value)
        
        tabs.on_value_change(on_tab_change)
        
        # 设置初始选中的Tab（在事件绑定后）
        tabs.value = initial_tab
        
        return tabs, tab_objects
    
    def render_tab_panels(self, tab_configs: Dict[str, Tuple[str, Callable]]):
        """渲染Tab面板内容"""
        if not self._tabs:
            raise ValueError("必须先调用 create_tabs_with_memory")
            
        with ui.tab_panels(self._tabs, value=self._tabs.value):
            for tab_key, (_, content_function) in tab_configs.items():
                with ui.tab_panel(tab_key):
                    content_function()
    
    def get_current_tab(self) -> str:
        """获取当前选中的Tab"""
        return self._tab_states.get(self.memory_key, self.default_tab or '')


def create_memorable_tabs(
    memory_key: str,
    tab_configs: Dict[str, Tuple[str, Callable]],
    default_tab: Optional[str] = None
) -> SimpleTabMemory:
    """
    便捷函数：创建带记忆功能的Tabs
    
    Args:
        memory_key: 用于区分不同页面的唯一标识
        tab_configs: Tab配置字典 {tab_key: (tab_label, content_function)}
        default_tab: 默认选中的Tab键值
    
    Returns:
        Tab记忆管理器实例
    """
    manager = SimpleTabMemory(memory_key, default_tab)
    tabs, tab_objects = manager.create_tabs_with_memory(tab_configs)
    manager.render_tab_panels(tab_configs)
    return manager


# 兼容性：保持旧的类名和函数名
TabMemoryManager = SimpleTabMemory