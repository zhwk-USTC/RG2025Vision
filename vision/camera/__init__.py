"""
摄像头模块

提供摄像头发现、连接、配置、标定和数据获取的功能。
"""

from .camera import Camera, save_config, load_config, camera_info_list, setup_camera_info
from .intrinsics import CameraIntrinsics, DEFAULT_INTRINSICS
from .calibration import CameraCalibrator

# ====== 全局摄像头管理 ======

# 创建三个摄像头实例 (前中后)
cameras = [Camera(), Camera(), Camera()]

# 初始加载配置
load_config(cameras)

__all__ = [
    'Camera',
    'cameras',
    'CameraIntrinsics',
    'DEFAULT_INTRINSICS',
    'CameraCalibrator',
    'camera_info_list',
    'setup_camera_info',
    'save_config',
    'load_config'
]
