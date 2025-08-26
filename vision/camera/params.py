"""
摄像头内参模块

提供摄像头内参的数据结构和相关操作。
"""

from dataclasses import dataclass, asdict
import numpy as np


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
    
    @property
    def camera_matrix(self):
        """获取相机矩阵 (3x3)"""
        return np.array([
            [self.fx, 0,      self.cx],
            [0,      self.fy, self.cy],
            [0,      0,       1]
        ])
    
    @property
    def distortion_coeffs(self):
        """获取畸变系数"""
        return np.array([self.k1, self.k2, self.p1, self.p2, self.k3])
    
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