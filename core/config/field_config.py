"""
场地配置管理模块
用于管理不同场地的AprilTag配置
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from core.config.config_manager import load_config, save_config
from core.paths import FIELD_CONFIG_PATH

@dataclass
class TagConfig:
    """单个Tag的配置"""
    tag_id: int
    tag_family: str = "tag36h11"  # tag25h9 或 tag36h11
    tag_size: float = 0.1  # Tag的物理尺寸，单位：米

@dataclass
class FieldConfig:
    """单个场地的配置"""
    name: str  # 场地名称
    tags: Dict[str, TagConfig] = field(default_factory=dict)  # 所有Tag的配置，key为tag_id

@dataclass
class FieldConfigManager:
    """场地配置管理器"""
    current_field: str = ""  # 当前选中的场地
    fields: Dict[str, FieldConfig] = field(default_factory=dict)  # 所有场地配置

# 全局配置管理器实例
_field_manager: Optional[FieldConfigManager] = None

def get_field_manager() -> FieldConfigManager:
    """获取场地配置管理器实例"""
    global _field_manager
    if _field_manager is None:
        _field_manager = load_field_config()
        if _field_manager is None:
            _field_manager = FieldConfigManager()

    return _field_manager

def load_field_config() -> Optional[FieldConfigManager]:
    """从文件加载场地配置"""
    return load_config(FIELD_CONFIG_PATH, FieldConfigManager)

def save_field_config():
    """保存场地配置到文件"""
    global _field_manager
    if _field_manager is not None:
        save_config(FIELD_CONFIG_PATH, _field_manager)

def get_current_field() -> FieldConfig:
    """获取当前场地配置"""
    manager = get_field_manager()
    if manager.current_field in manager.fields:
        return manager.fields[manager.current_field]
    else:
        # 如果当前场地不存在，返回第一个可用场地
        if manager.fields:
            first_field_key = list(manager.fields.keys())[0]
            manager.current_field = first_field_key
            return manager.fields[first_field_key]
        else:
            return FieldConfig(name="无可用场地")

def set_current_field(field_name: str) -> bool:
    """设置当前场地"""
    manager = get_field_manager()
    if field_name in manager.fields:
        manager.current_field = field_name
        return True
    return False

def add_tag(tag_name: str, tag_config: TagConfig, field_name: Optional[str] = None) -> bool:
    """向当前场地添加或更新Tag配置"""
    manager = get_field_manager()
    if field_name is None:
        field_name = manager.current_field
    if field_name in manager.fields:
        field = manager.fields[field_name]
        field.tags[tag_name] = tag_config
        return True
    return False

def get_tag_id(tag_name: str, field_name: Optional[str] = None) -> int:
    """获取当前场地的指定Tag ID"""
    manager = get_field_manager()
    if field_name is None:
        field_name = manager.current_field
    return manager.fields[field_name].tags.get(tag_name, TagConfig(tag_id=-1)).tag_id

def list_available_fields() -> Dict[str, str]:
    """列出所有可用场地"""
    manager = get_field_manager()
    return {key: field.name for key, field in manager.fields.items()}

def add_field(key: str, field_config: FieldConfig):
    """添加新场地配置"""
    manager = get_field_manager()
    manager.fields[key] = field_config

def remove_field(key: str) -> bool:
    """删除场地配置"""
    manager = get_field_manager()
    if key in manager.fields:
        del manager.fields[key]
        # 如果删除的是当前场地，切换到第一个可用场地
        if manager.current_field == key:
            if manager.fields:
                manager.current_field = list(manager.fields.keys())[0]
            else:
                manager.current_field = ""
        return True
    return False