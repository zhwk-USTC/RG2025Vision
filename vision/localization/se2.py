import math
import numpy as np

ArrayLike = np.ndarray

def to_homogeneous_2d(yaw: float, t: ArrayLike) -> ArrayLike:
    """构造 3×3 二维齐次变换矩阵 T = [R t; 0 0 1]（A←B）"""
    c, s = math.cos(yaw), math.sin(yaw)
    T = np.eye(3, dtype=float)
    T[0, 0] = c
    T[0, 1] = -s
    T[1, 0] = s
    T[1, 1] = c
    t = np.asarray(t, dtype=float).reshape(2)
    T[0:2, 2] = t
    return T


def invert_homogeneous_2d(T: ArrayLike) -> ArrayLike:
    """计算 3×3 二维齐次矩阵的逆"""
    R = T[:2, :2]
    t = T[:2, 2]
    Tinv = np.eye(3, dtype=float)
    Tinv[:2, :2] = R.T
    Tinv[:2, 2] = -R.T @ t
    return Tinv


def mat2d_to_yaw(R: ArrayLike) -> float:
    """从二维旋转矩阵中提取 yaw（弧度）"""
    return float(math.atan2(R[1, 0], R[0, 0]))
