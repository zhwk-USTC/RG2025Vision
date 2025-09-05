# vision/estimation/se2.py
import math
from typing import Iterable, Tuple
import numpy as np

ArrayLike = np.ndarray


def _as_xy(t) -> np.ndarray:
    """确保平移是形状 (2,) 的 float 向量。"""
    return np.asarray(t, dtype=float).reshape(2)


def to_homogeneous_2d(yaw: float, t: ArrayLike) -> ArrayLike:
    """构造 3×3 二维齐次变换矩阵 T = [R t; 0 0 1]（A←B）"""
    c, s = math.cos(yaw), math.sin(yaw)
    T = np.eye(3, dtype=float)
    T[0, 0] = c;  T[0, 1] = -s
    T[1, 0] = s;  T[1, 1] =  c
    T[0:2, 2] = _as_xy(t)
    return T


def invert_homogeneous_2d(T: ArrayLike) -> ArrayLike:
    """计算 3×3 二维齐次矩阵的逆"""
    T = np.asarray(T, dtype=float)
    R = T[:2, :2]
    t = T[:2, 2]
    Tinv = np.eye(3, dtype=float)
    Rt = R.T
    Tinv[:2, :2] = Rt
    Tinv[:2, 2] = -Rt @ t
    return Tinv


def mat2d_to_yaw(R: ArrayLike) -> float:
    """从二维旋转矩阵中提取 yaw（弧度）"""
    R = np.asarray(R, dtype=float)
    return float(math.atan2(R[1, 0], R[0, 0]))


# ---- 可选便捷函数（不影响现有调用） ----

def compose(Ta: ArrayLike, Tb: ArrayLike) -> ArrayLike:
    """组合两个 SE(2) 齐次矩阵：Tc = Ta @ Tb"""
    return np.asarray(Ta, float) @ np.asarray(Tb, float)


def from_pose(x: float, y: float, yaw: float) -> ArrayLike:
    """由 (x,y,yaw) 直接构造 3×3 齐次矩阵。"""
    return to_homogeneous_2d(yaw, np.array([x, y], dtype=float))


def to_pose(T: ArrayLike) -> Tuple[float, float, float]:
    """把 3×3 齐次矩阵还原为 (x, y, yaw)。"""
    T = np.asarray(T, dtype=float)
    x, y = float(T[0, 2]), float(T[1, 2])
    yaw = mat2d_to_yaw(T[:2, :2])
    return x, y, yaw


def transform_points(T: ArrayLike, pts_xy: Iterable[Iterable[float]]) -> np.ndarray:
    """将一组二维点（N×2）用 SE(2) 变换到新坐标系。"""
    T = np.asarray(T, float)
    P = np.asarray(pts_xy, float).reshape(-1, 2)
    R = T[:2, :2]; t = T[:2, 2]
    return (P @ R.T) + t


def is_valid_se2(T: ArrayLike, atol: float = 1e-6) -> bool:
    """简单校验矩阵是否近似符合 SE(2)。"""
    T = np.asarray(T, float)
    if T.shape != (3, 3): return False
    if not np.allclose(T[2], [0, 0, 1], atol=atol): return False
    R = T[:2, :2]
    return np.allclose(R.T @ R, np.eye(2), atol=atol)
