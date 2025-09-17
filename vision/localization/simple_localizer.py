# vision/localization/simple_localizer.py

import math
from typing import Optional, Tuple

import cv2
import numpy as np

from .types import CameraPose  # x, y, z, roll, pitch, yaw
from ..detection.apriltag import TagDetection


# ---------- 工具 ----------
def rpy_to_R(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """ZYX欧拉：R = Rz(yaw) @ Ry(pitch) @ Rx(roll)"""
    cr, sr = math.cos(roll),  math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw),   math.sin(yaw)
    Rx = np.array([[1, 0, 0],
                   [0, cr, -sr],
                   [0, sr,  cr]], dtype=float)
    Ry = np.array([[cp, 0, sp],
                   [0,  1, 0 ],
                   [-sp,0, cp]], dtype=float)
    Rz = np.array([[cy, -sy, 0],
                   [sy,  cy, 0],
                   [0,    0, 1]], dtype=float)
    return Rz @ Ry @ Rx

def R_to_rpy_zyx(R: np.ndarray) -> Tuple[float, float, float]:
    """返回 (roll, pitch, yaw)；ZYX"""
    R = np.asarray(R, float)
    sy = -R[2, 0]
    sy = max(min(sy, 1.0), -1.0)
    pitch = math.asin(sy)
    if abs(abs(pitch) - math.pi/2) < 1e-6:
        roll = 0.0
        yaw  = math.atan2(-R[0,1], R[1,1])
    else:
        roll = math.atan2(R[2,1], R[2,2])
        yaw  = math.atan2(R[1,0], R[0,0])
    return roll, pitch, yaw

def project_to_so3(R: np.ndarray) -> np.ndarray:
    """投影到最近的 SO(3)：正交化并确保 det=+1。"""
    R = np.asarray(R, float)
    U, _, Vt = np.linalg.svd(R)
    Rn = U @ Vt
    if np.linalg.det(Rn) < 0.0:
        U[:, -1] *= -1.0
        Rn = U @ Vt
    return Rn

def to_R(r_or_R) -> np.ndarray:
    """接受 3x3 R 或 3x1/1x3 rvec（Rodrigues），返回 3x3 R。"""
    arr = np.asarray(r_or_R, float)
    if arr.shape == (3, 3):
        return arr
    flat = arr.reshape(-1)
    if flat.shape[0] == 3:
        R, _ = cv2.Rodrigues(flat.reshape(3, 1))
        return R
    raise ValueError(f"pose_R/pose_rvec shape invalid: {arr.shape}")

def se3(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    T = np.eye(4, dtype=float)
    T[:3, :3] = R
    T[:3, 3]  = np.asarray(t, float).reshape(3)
    return T

def inv_se3(T: np.ndarray) -> np.ndarray:
    R = T[:3, :3]
    t = T[:3, 3]
    Ti = np.eye(4, dtype=float)
    Rt = R.T
    Ti[:3, :3] = Rt
    Ti[:3, 3]  = -Rt @ t
    return Ti

def T_to_xyzrpy(T: np.ndarray) -> Tuple[float, float, float, float, float, float]:
    R = T[:3, :3]
    t = T[:3, 3]
    roll, pitch, yaw = R_to_rpy_zyx(R)
    return float(t[0]), float(t[1]), float(t[2]), float(roll), float(pitch), float(yaw)


# ---------- 定位器（在 Tag 帧去 yaw 然后输出 Camera@Tag） ----------
class SingleTagLocalizer:
    """
    流程：
      1) 输入 tag→camera: (R_ct, t_ct)
      2) 对 R_ct 做 ZYX 分解得到 yaw_ct
      3) 在 Tag 帧右乘 Rz(-yaw_ct)：R_ct_no_yaw = R_ct · Rz(-yaw_ct)
      4) T_ct = [R_ct_no_yaw, t_ct]，取逆 T_tc = T_ct^{-1}
      5) 输出 CameraPose（Camera 在 Tag 系）
    说明：右乘表示在 Tag 自身 z 轴上“转回去”，只改朝向不改位置。
    """

    MIN_RANGE_M: float = 0.05
    YAW_EPS: float = 1e-2  # 打印前的小角度归零阈值（弧度）

    def update(self, det: Optional[TagDetection]) -> Optional[CameraPose]:
        if det is None:
            return None

        # 兼容不同字段名
        R_or_r = getattr(det, "pose_R", None)
        if R_or_r is None:
            R_or_r = getattr(det, "rvec", None)
        t = getattr(det, "pose_t", None)
        if t is None:
            t = getattr(det, "tvec", None)
        if R_or_r is None or t is None:
            return None

        # tag->camera
        R_ct = to_R(R_or_r)
        t_ct = np.asarray(t, float).reshape(3)

        # 基本有效性
        if not np.isfinite(R_ct).all() or not np.isfinite(t_ct).all():
            return None
        if np.linalg.norm(t_ct) < self.MIN_RANGE_M:
            return None

        # 数值稳健
        R_ct = project_to_so3(R_ct)

        # --- 去掉 tag 在相机前的平面内自转（保持 z 轴，重建 x/y）---
        # 原旋转矩阵的三列：分别是 tag 的 x,y,z 轴在相机坐标系下的表示
        z_c = R_ct[:, 2]                         # 保留法向量（倾斜信息）
        z_c = z_c / np.linalg.norm(z_c)

        # 选一个参考方向供投影（避免与 z_c 平行退化）
        ref = np.array([1.0, 0.0, 0.0])
        if abs(float(np.dot(ref, z_c))) > 0.95:
            ref = np.array([0.0, 1.0, 0.0])

        # 在 tag 平面内构造“无自转”的 x 轴：把参考方向投影到 tag 平面并归一化
        x_c = ref - z_c * float(np.dot(ref, z_c))
        x_c = x_c / np.linalg.norm(x_c)

        # y 轴由右手系叉积得到
        y_c = np.cross(z_c, x_c)

        # 重建去 yaw 的旋转（列为 x,y,z）
        R_ct_no_yaw = np.column_stack((x_c, y_c, z_c))
        R_ct_no_yaw = project_to_so3(R_ct_no_yaw)

        # 构造 T_ct 并求逆得到 T_tc（camera 在 tag 系）
        T_ct = se3(R_ct_no_yaw, t_ct)
        T_tc = inv_se3(T_ct)

        # 输出 CameraPose（camera 相对 tag）
        x, y, z, roll_tc, pitch_tc, yaw_tc = T_to_xyzrpy(T_tc)

        # 打印前的容差归零，抑制数值残差显示
        if abs(yaw_tc) < self.YAW_EPS:
            yaw_tc = 0.0

        return CameraPose(x, y, z, roll_tc, pitch_tc, yaw_tc)
