from dataclasses import dataclass


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
    