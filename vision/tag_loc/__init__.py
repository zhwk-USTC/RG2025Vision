"""AprilTag 多摄像头二维定位模块（融合多相机观测到已知 Tag 地图）

公开 API:
- CameraPose, TagPose, CarPose
- Localization
"""

from .types import TagPose, CarPose
from .localization import Localization

__all__ = [
    "TagPose",
    "CarPose",
    "Localization",
]
