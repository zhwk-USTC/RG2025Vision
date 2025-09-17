from dataclasses import dataclass

@dataclass(slots=True)
class TagPose:
    """AprilTag 在场地（world）坐标系中的二维位姿（x, y, yaw）
    - x, y: 标签中心位置（m）
    - yaw: 旋转角度（弧度）
    表示 T_world_tag : world ← tag
    """
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float
    
    
    
@dataclass(slots=True)    
class CameraPose:
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float
    
    
