from dataclasses import dataclass

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
    

@dataclass(slots=True)
class CarPose:
    """小车二维位姿 (x, y, yaw)，单位米/弧度
    表示 T_world_car : world ← car
    """
    x: float
    y: float
    yaw: float
