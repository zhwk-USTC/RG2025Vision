# vision/estimation/__init__.py
"""
AprilTag 多摄像头二维定位模块（融合多相机观测到已知 Tag 地图）

公开 API:
- CameraPose, TagPose, CarPose
- Localizer
"""
from ..types.tag_types import TagPose, CarPose
from .localizer import Localizer  # 修正：此前误写为 localization

TAG_SIZE_M: float = 0.15

__all__ = ["TagPose", "CarPose", "Localizer", "TAG_SIZE_M"]
