"""
场地配置管理模块
用于管理不同场地的AprilTag配置
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from core.config.config_manager import load_config, save_config
from core.paths import CONFIG_DIR
import os

# 场地配置文件路径
FIELD_CONFIG_PATH = os.path.join(CONFIG_DIR, "field_config.json")

@dataclass
class TagConfig:
    """单个Tag的配置"""
    tag_id: int
    tag_family: str = "tag36h11"  # tag25h9 或 tag36h11
    tag_size: float = 0.1  # Tag的物理尺寸，单位：米
    description: str = ""  # 描述信息

@dataclass
class FieldConfig:
    """单个场地的配置"""
    name: str  # 场地名称
    description: str = ""  # 场地描述
    
    # 关键位置的Tag配置
    firespot_tag: Optional[TagConfig] = None  # 发射架Tag
    target_tags: Dict[str, TagConfig] = field(default_factory=dict)  # 目标Tag字典
    navigation_tags: Dict[str, TagConfig] = field(default_factory=dict)  # 导航Tag字典
    
    def __post_init__(self):
        # 如果没有设置发射架Tag，使用默认值
        if self.firespot_tag is None:
            self.firespot_tag = TagConfig(tag_id=1, description="发射架")

@dataclass
class FieldConfigManager:
    """场地配置管理器"""
    current_field: str = "field_a"  # 当前选中的场地，默认为场地A
    fields: Dict[str, FieldConfig] = field(default_factory=dict)  # 所有场地配置
    
    def __post_init__(self):
        if not self.fields:
            # 创建场地配置
            self._create_field_configs()
    
    def _create_field_configs(self):
        """创建场地配置"""
        # 比赛场地A
        field_a = FieldConfig(
            name="比赛场地A",
            description="正式比赛场地A的配置",
            firespot_tag=TagConfig(tag_id=5, description="发射架A"),
            target_tags={
                "red": TagConfig(tag_id=6, description="红色目标A"),
                "blue": TagConfig(tag_id=7, description="蓝色目标A")
            },
            navigation_tags={
                "start": TagConfig(tag_id=20, description="起始点A"),
                "checkpoint1": TagConfig(tag_id=21, description="检查点A1"),
                "checkpoint2": TagConfig(tag_id=22, description="检查点A2")
            }
        )
        
        # 比赛场地B
        field_b = FieldConfig(
            name="比赛场地B",
            description="正式比赛场地B的配置",
            firespot_tag=TagConfig(tag_id=8, description="发射架B"),
            target_tags={
                "red": TagConfig(tag_id=9, description="红色目标B"),
                "blue": TagConfig(tag_id=15, description="蓝色目标B")
            },
            navigation_tags={
                "start": TagConfig(tag_id=30, description="起始点B"),
                "checkpoint1": TagConfig(tag_id=31, description="检查点B1"),
                "checkpoint2": TagConfig(tag_id=32, description="检查点B2")
            }
        )
        
        self.fields = {
            "field_a": field_a,
            "field_b": field_b
        }

# 全局配置管理器实例
_field_manager: Optional[FieldConfigManager] = None

def get_field_manager() -> FieldConfigManager:
    """获取场地配置管理器实例"""
    global _field_manager
    if _field_manager is None:
        _field_manager = load_field_config()
        if _field_manager is None:
            _field_manager = FieldConfigManager()
            save_field_config()
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
            save_field_config()
            return manager.fields[first_field_key]
        else:
            return FieldConfig(name="无可用场地")

def set_current_field(field_name: str) -> bool:
    """设置当前场地"""
    manager = get_field_manager()
    if field_name in manager.fields:
        manager.current_field = field_name
        save_field_config()
        return True
    return False

def get_firespot_tag_id() -> int:
    """获取当前场地的发射架Tag ID"""
    current = get_current_field()
    return current.firespot_tag.tag_id if current.firespot_tag else 1

def get_target_tag_id(color: str) -> Optional[int]:
    """获取指定颜色目标的Tag ID"""
    current = get_current_field()
    if color in current.target_tags:
        return current.target_tags[color].tag_id
    return None

def get_navigation_tag_id(point: str) -> Optional[int]:
    """获取指定导航点的Tag ID"""
    current = get_current_field()
    if point in current.navigation_tags:
        return current.navigation_tags[point].tag_id
    return None

def list_available_fields() -> Dict[str, str]:
    """列出所有可用场地"""
    manager = get_field_manager()
    return {key: field.name for key, field in manager.fields.items()}

def add_field(key: str, field_config: FieldConfig):
    """添加新场地配置"""
    manager = get_field_manager()
    manager.fields[key] = field_config
    save_field_config()

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
        save_field_config()
        return True
    return False