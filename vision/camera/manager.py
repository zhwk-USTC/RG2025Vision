import cv2
import platform
from typing import Optional, Any, List
from cv2_enumerate_cameras import enumerate_cameras
from cv2_enumerate_cameras.camera_info import CameraInfo

from core.logger import logger

_camera_info_list: List[CameraInfo] = []


def scan_cameras() -> List[CameraInfo]:
    """初始化摄像头信息"""
    # 根据操作系统选择合适的摄像头后端
    if platform.system() == "Windows":
        backend = cv2.CAP_MSMF
    elif platform.system() == "Linux":
        backend = cv2.CAP_V4L2
    else:  # macOS
        backend = cv2.CAP_AVFOUNDATION

    global _camera_info_list
    _camera_info_list = enumerate_cameras(backend)

    for info in _camera_info_list:
        info.name = info.name + f" ({info.index})"

    logger.info(f"已找到 {len(_camera_info_list)} 个摄像头")
    for idx, info in enumerate(_camera_info_list):
        name = getattr(info, 'name', None)
        logger.info(f"  [{idx}] {name if name else info}")
    return _camera_info_list

def get_camera_info_list() -> List[CameraInfo]:
    return _camera_info_list