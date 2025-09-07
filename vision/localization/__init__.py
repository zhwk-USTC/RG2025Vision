# vision/estimation/__init__.py
"""
AprilTag 多摄像头二维定位模块（融合多相机观测到已知 Tag 地图）

公开 API:
- TagPose, CarPose
- Localizer
"""
from .localizer import Localizer, LocalizerConfig
from .types import TagPose, CarPose, CameraPose


__all__ = ["TagPose", "CarPose", "CameraPose", "Localizer", "LocalizerConfig"]
