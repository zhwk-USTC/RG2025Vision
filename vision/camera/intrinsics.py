"""
摄像头内参模块

提供摄像头内参的数据结构和相关操作。
"""

from dataclasses import dataclass, asdict
import numpy as np


@dataclass
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
    
    def __post_init__(self):
        """初始化后的处理"""
        # 将dataclass的width和height属性同步到内部的_image_width和_image_height
        self._image_width = self.width
        self._image_height = self.height
    
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
    
    @property
    def fov_horizontal(self):
        """计算水平视场角(FOV)，单位：弧度
        
        视场角 = 2 * arctan(sensor_width / (2 * focal_length))
        由于我们没有物理传感器宽度信息，这里使用像素宽度和fx计算
        
        注意：如果fx为0或接近0，将返回π/2
        """
        if abs(self.fx) < 1e-6:  # 避免除以0
            return np.pi / 2
        return 2 * np.arctan2(self.width / 2, self.fx)
    
    @property
    def fov_vertical(self):
        """计算垂直视场角(FOV)，单位：弧度
        
        注意：如果fy为0或接近0，将返回π/2
        """
        if abs(self.fy) < 1e-6:  # 避免除以0
            return np.pi / 2
        return 2 * np.arctan2(self.height / 2, self.fy)
    
    def set_image_size(self, width: int, height: int):
        """设置图像大小，用于更准确地计算视场角
        
        Args:
            width: 图像宽度（像素）
            height: 图像高度（像素）
        """
        self._image_width = width
        self._image_height = height
        # 同步更新dataclass的属性
        self.width = width
        self.height = height

