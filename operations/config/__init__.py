"""
Operations配置管理模块
用于管理操作相关的配置文件
"""

# 导出主要的配置类和函数
from .operation_config import (
    OperationNodeConfig,
    OperationConfig,
    OperationConfigManager,
    get_operation_manager,
    load_operation_config,
    save_operation_config,
    get_current_operation,
    set_current_operation,
    save_current_operation,
    list_available_operations,
    add_operation,
    remove_operation,
)

__all__ = [
    "OperationNodeConfig",
    "OperationConfig",
    "OperationConfigManager",
    "get_operation_manager",
    "load_operation_config",
    "save_operation_config",
    "get_current_operation",
    "set_current_operation",
    "save_current_operation",
    "list_available_operations",
    "add_operation",
    "remove_operation",
]
