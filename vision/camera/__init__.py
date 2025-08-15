"""
摄像头模块

提供摄像头发现、连接、配置、标定和数据获取的功能。
"""

from .camera import Camera, camera_info_list, setup_camera_info
from .camera_config import save_config, load_config, load_intrinsics
from .intrinsics import CameraIntrinsics

# ====== 全局摄像头管理 ======

# 创建三个摄像头实例 (前中后)
cameras = [Camera(), Camera(), Camera()]

# 初始加载配置
from .camera_config import load_config
load_config(cameras)
load_intrinsics(cameras)

__all__ = [
    'Camera',
    'cameras',
    'CameraIntrinsics',
    'load_intrinsics',
    'camera_info_list',
    'setup_camera_info',
    'save_config',
    'load_config'
]
