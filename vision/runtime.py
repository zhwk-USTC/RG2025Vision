# vision/runtime.py
"""
VisionSystem 单例管理与启动逻辑。
提供统一接口来初始化、获取、重置 VisionSystem 实例，并管理其生命周期。
"""

from typing import Optional
from threading import Lock
from .vision_system import VisionSystem, VisionSystemConfig
from core.logger import logger
from core.config import load_config, VISION_CONFIG_PATH, save_config

# 全局变量：保存单例 VisionSystem
_vs: Optional[VisionSystem] = None
_lock = Lock()  # 用于线程安全地访问 _vs

def is_vision_initialized() -> bool:
    """
    检查 VisionSystem 是否已初始化。

    Returns:
        bool: 如果已初始化，返回 True；否则返回 False。
    """
    with _lock:
        return _vs is not None

def get_vision() -> VisionSystem:
    """
    获取当前的 VisionSystem 单例实例。
    如果实例尚未初始化，返回 None。

    Returns:
        VisionSystem | None: 当前单例实例或 None（未初始化）
    """
    with _lock:
        if _vs is None:
            raise RuntimeError("VisionSystem 尚未初始化")
        return _vs

def init_vision() -> VisionSystem:
    """
    初始化 VisionSystem 实例，并加载配置。
    如果实例已经存在，则返回已有实例。

    Returns:
        VisionSystem: 当前的单例实例
    """
    global _vs
    with _lock:
        if _vs is None:
            vision_config = load_config(VISION_CONFIG_PATH, VisionSystemConfig)
            if not vision_config:
                logger.warning("未能加载视觉系统配置，使用空白配置")
            else:
                logger.info(f"已加载视觉系统配置")
            _vs = VisionSystem(vision_config)
            logger.info(f"[VisionSystem] 已初始化实例，包含 {len(_vs._cameras)} 个相机节点")
        else:
            logger.info(f"[VisionSystem] 已存在实例，使用现有实例")
        return _vs

def start_vision() -> None:
    """
    启动 VisionSystem 实例，连接所有相机。
    如果实例尚未初始化，则先进行初始化。

    Raises:
        RuntimeError: 如果启动过程中出现错误
    """
    vs = get_vision()
    ok = vs.start()
    if not ok:
        raise RuntimeError("VisionSystem 启动失败，检查相机连接")
    logger.info("VisionSystem 已启动")
    
    
def reset_vision() -> None:
    """
    重置 VisionSystem 单例实例，销毁当前实例并清空全局存储。
    在重置后，下一次调用 `init_vision()` 时会重新创建实例。

    注意：
        - 调用此方法后，原实例将被销毁（通过调用 `close()` 释放资源）
        - 适用于需要重新初始化系统的场景
    """
    global _vs
    old: Optional[VisionSystem] = None
    with _lock:
        if _vs is not None:
            old = _vs
            _vs = None  # 将单例指针置为空
    # 在锁外进行销毁与清理操作，避免死锁
    if old is not None:
        old.close()  # 调用 VisionSystem 的关闭方法，释放资源

def save_vision_config() -> None:
    """
    保存当前 VisionSystem 的配置到文件。
    如果实例尚未初始化，则不执行任何操作。
    """
    if not is_vision_initialized():
        logger.error("VisionSystem 未初始化，无法保存配置")
        return
    vs = get_vision()
    config = vs.get_config()
    save_config(VISION_CONFIG_PATH, config)
    logger.info("已保存视觉系统配置")