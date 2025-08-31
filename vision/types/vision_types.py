"""
摄像头内参模块

提供摄像头内参的数据结构和相关操作。
"""

from dataclasses import dataclass, field
from typing import Optional, List

# 摄像头基础配置

@dataclass(slots=True)
class CameraConfig:
    index:int = -1
    width:int = 1920
    height:int = 1080
    fps:float = 30.0

@dataclass(slots=True)
class CameraIntrinsics:
    """摄像头内参类
    
    代表摄像头的内部参数，包括:
    - 焦距 (fx, fy)
    - 光学中心点 (cx, cy)
    - 畸变系数 (k1, k2, p1, p2, k3)
    - 图像尺寸 (用于计算FOV)
    """
    width: int
    height: int
    
    fx: float  # 焦距x
    fy: float  # 焦距y
    cx: float  # 光学中心x
    cy: float  # 光学中心y
    # 畸变系数
    k1: float = 0.0
    k2: float = 0.0
    p1: float = 0.0
    p2: float = 0.0
    k3: float = 0.0
    
@dataclass(slots=True)
class CameraPose:
    """摄像头在小车坐标系下的二维外参（x, y, yaw）
    - x, y: 平移（m）
    - yaw: 旋转角度（弧度）
    表示  T_car_cam : car ← cam
    """
    x: float
    y: float
    yaw: float
    
# apriltag检测配置

from pyapriltags import Detection
TagDetection = Detection

TagDetections = List[TagDetection]

@dataclass(slots=True)
class TagDetectionConfig:
    families: str = 'tag36h11'
    nthreads: int = 1
    quad_decimate: float = 2.0
    quad_sigma: float = 0.0
    refine_edges: int = 1
    decode_sharpening: float = 0.25
    debug: int = 0

@dataclass(slots=True)
class TagPose:
    """AprilTag 在场地（world）坐标系中的二维位姿（x, y, yaw）
    - x, y: 标签中心位置（m）
    - yaw: 旋转角度（弧度）
    表示 T_world_tag : world ← tag
    """
    id: int
    x: float
    y: float
    yaw: float

# 节点与模块配置

@dataclass(slots=True)
class CarPose:
    """小车二维位姿 (x, y, yaw)，单位米/弧度
    表示 T_world_car : world ← car
    """
    x: float
    y: float
    yaw: float


@dataclass(slots=True)
class CamNodeConfig:
    """摄像头节点配置类"""
    alias: str = "未命名"
    camera: Optional[CameraConfig] = None
    intrinsics: Optional[CameraIntrinsics] = None
    pose: Optional[CameraPose] = None

    tag36h11: Optional[TagDetectionConfig] = None
    
@dataclass
class VisionSystemConfig:
    cam_nodes: List[CamNodeConfig] = field(default_factory=list)