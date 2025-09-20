from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from core.config.config_manager import load_config, save_config
from core.paths import TASKS_CONFIG_PATH

@dataclass
class OperationNodeConfig:
    """节点配置基类"""
    type: Literal["task", "condition", "target"]  # 节点类型
    id: str = ""    # 节点唯一标识
    name: str = ""  # 节点名称
    parameters: Dict[str, Any] = field(default_factory=dict)  # 节点参数

@dataclass
class OperationConfig:
    """混合任务配置（支持任务节点和条件分支节点）"""
    nodes: List[OperationNodeConfig] = field(default_factory=list)  # 任务/节点列表，按顺序执行
    description: str = ""  # 配置描述


def load_operation_config() -> OperationConfig:
    """从文件加载混合任务配置"""
    config = load_config(TASKS_CONFIG_PATH, OperationConfig)
    if config is None:
        config = OperationConfig()
    return config


def save_operation_config(config: OperationConfig):
    """保存混合任务配置到文件"""
    save_config(TASKS_CONFIG_PATH, config)