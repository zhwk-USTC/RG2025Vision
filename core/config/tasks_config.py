from dataclasses import dataclass, field
from typing import List
from core.config.config_manager import load_config, save_config
from core.paths import TASKS_CONFIG_PATH

@dataclass
class StepConfig:
    """单个任务步骤的配置"""
    name: str  # 任务步骤名称
    parameters: dict = field(default_factory=dict)  # 任务步骤参数

@dataclass
class TasksConfig:
    tasks: List[StepConfig] = field(default_factory=list)  # 任务列表，按顺序执行


def load_tasks_config() -> TasksConfig:
    """从文件加载任务配置"""
    config = load_config(TASKS_CONFIG_PATH, TasksConfig)
    if config is None:
        config = TasksConfig()
    return config

def save_tasks_config(config: TasksConfig):
    """保存任务配置到文件"""
    save_config(TASKS_CONFIG_PATH, config)