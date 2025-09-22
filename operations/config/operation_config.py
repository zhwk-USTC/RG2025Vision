"""
工作流程配置管理模块
用于管理不同的任务流程配置
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from core.config.config_manager import load_config, save_config
from core.paths import OPERATION_CONFIG_DIR
import os

OPERATION_MANAGER_PATH = os.path.join(OPERATION_CONFIG_DIR, ".manager.json")

def OPERATION_CONFIG_PATH(operation_name: str) -> str:
    """获取指定工作流程的配置文件路径"""
    filename = f"{operation_name}.json"
    return os.path.join(OPERATION_CONFIG_DIR, filename)

@dataclass
class OperationNodeConfig:
    """节点配置基类
    type:
      - 'task'：可执行任务节点
      - 'condition'：条件判断节点
      - 'target'：条件跳转目标锚点
      - 'note'：仅显示文字的注释节点（新增）
        - 建议将正文存放在 parameters['text'] 中
    """
    type: Literal["task", "condition", "target", "note"]  # ← 新增 "note"
    id: str = ""    # 节点唯一标识（note 可留空或按需生成）
    name: str = ""  # 节点名称（note 可做标题/留空）
    parameters: Dict[str, Any] = field(default_factory=dict)  # 节点参数（note: 放置 'text' 等）

@dataclass
class OperationConfig:
    """单个工作流程的配置"""
    name: str  # 流程名称
    description: str = ""  # 流程描述
    nodes: List[OperationNodeConfig] = field(default_factory=list)  # 任务/节点列表，按顺序执行

@dataclass
class OperationConfigManager:
    """工作流程配置管理器"""
    current_operation: str = ""  # 当前选中的工作流程
    operations: List[str] = field(default_factory=list)  # 只存储工作流程名称列表

# 全局配置管理器实例
_operation_manager: Optional[OperationConfigManager] = None

def get_operation_manager() -> OperationConfigManager:
    """获取工作流程配置管理器实例"""
    global _operation_manager
    if _operation_manager is None:
        _operation_manager = load_operation_manager()
        if _operation_manager is None:
            _operation_manager = OperationConfigManager()

    return _operation_manager

def load_operation_manager() -> OperationConfigManager:
    """加载工作流程配置管理器"""
    manager = load_config(OPERATION_MANAGER_PATH, OperationConfigManager)
    if manager is None:
        manager = OperationConfigManager()
        save_config(OPERATION_MANAGER_PATH, manager)
    return manager

def save_operation_manager() -> None:
    """保存工作流程配置管理器"""
    global _operation_manager
    if _operation_manager is not None:
        save_config(OPERATION_MANAGER_PATH, _operation_manager)

def load_operation_config(operation_name: str) -> Optional[OperationConfig]:
    """从文件加载工作流程配置"""
    return load_config(OPERATION_CONFIG_PATH(operation_name), OperationConfig)

def save_operation_config(operation_name: str, config: OperationConfig) -> None:
    """保存工作流程配置到文件"""
    global _operation_manager
    if _operation_manager is not None:
        save_config(OPERATION_CONFIG_PATH(operation_name), config)

def get_current_operation() -> OperationConfig:
    """获取当前工作流程配置"""
    manager = get_operation_manager()
    if manager.current_operation in manager.operations:
        return load_operation_config(manager.current_operation) or OperationConfig(name="无效工作流程")
    else:
        # 如果当前工作流程不存在，返回第一个可用流程
        if manager.operations:
            first_operation_name = list(manager.operations)[0]
            manager.current_operation = first_operation_name
            return load_operation_config(first_operation_name) or OperationConfig(name="无效工作流程")
        else:
            return OperationConfig(name="无可用工作流程")
        
def save_current_operation(config: OperationConfig) -> None:
    """保存当前工作流程配置"""
    manager = get_operation_manager()
    if manager.current_operation in manager.operations:
        save_operation_config(manager.current_operation, config)
    else:
        # 如果当前工作流程不存在，添加并保存
        if config.name not in manager.operations:
            manager.operations.append(config.name)
        manager.current_operation = config.name
        save_operation_manager()
        save_operation_config(config.name, config)

def set_current_operation(operation_name: str) -> bool:
    """设置当前工作流程"""
    manager = get_operation_manager()
    if operation_name in manager.operations:
        manager.current_operation = operation_name
        return True
    return False

def list_available_operations() -> List[str]:
    """列出所有可用的工作流程"""
    manager = get_operation_manager()
    return manager.operations

def add_operation(name: str, operation_config: OperationConfig):
    """添加新工作流程配置"""
    manager = get_operation_manager()
    if name not in manager.operations:
        manager.operations.append(name)
    save_operation_config(name, operation_config)

def remove_operation(key: str) -> bool:
    """删除工作流程配置"""
    manager = get_operation_manager()
    if key in manager.operations:
        manager.operations.remove(key)
        # 如果删除的是当前工作流程，切换到第一个可用流程
        if manager.current_operation == key:
            if manager.operations:
                manager.current_operation = manager.operations[0]
            else:
                manager.current_operation = ""
        return True
    return False