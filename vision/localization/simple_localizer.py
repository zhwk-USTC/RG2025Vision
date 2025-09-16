# vision/localization/simple_localizer.py

import math
from typing import Optional, List, Tuple

import cv2
import numpy as np

from .types import TagPose, CameraPose
from ..detection.apriltag import TagDetection


# ---------- 工具 ----------
def rpy_to_R(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """ZYX: R = Rz(yaw) @ Ry(pitch) @ Rx(roll)"""
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
    """数值投影到最近的 SO(3)：正交化并确保 det=+1。"""
    R = np.asarray(R, float)
    U, _, Vt = np.linalg.svd(R)
    Rn = U @ Vt
    if np.linalg.det(Rn) < 0.0:
        U[:, -1] *= -1.0
        Rn = U @ Vt
    return Rn

def zero_roll_zyx(R: np.ndarray) -> np.ndarray:
    """将输入旋转矩阵按 ZYX 分解后把 roll 设为 0，再重建矩阵（含 SO(3) 投影）。"""
    r, p, y = R_to_rpy_zyx(R)
    R0 = rpy_to_R(0.0, p, y)
    return project_to_so3(R0)

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

def to_R(r_or_R) -> np.ndarray:
    arr = np.asarray(r_or_R, float)
    if arr.shape == (3, 3):
        return arr
    flat = arr.reshape(-1)
    if flat.shape[0] == 3:
        R, _ = cv2.Rodrigues(flat.reshape(3, 1))
        return R
    raise ValueError(f"pose_R/pose_rvec shape invalid: {arr.shape}")

def T_to_xyzrpy(T: np.ndarray) -> Tuple[float, float, float, float, float, float]:
    R = T[:3, :3]
    t = T[:3, 3]
    roll, pitch, yaw = R_to_rpy_zyx(R)
    return float(t[0]), float(t[1]), float(t[2]), float(roll), float(pitch), float(yaw)


# ---------- 定位器 ----------
class SingleTagLocalizer:
    """
    单相机·单Tag 三维定位（右手系：x前、y左、z上；角为弧度，ZYX）
    输入：
      - Apriltag detection 的 (R_ct, t_ct) 表示 tag→camera
      - 先验：Tag 在世界系 T_world_tag（可通过 set_tag_pose 更新）
    输出：
      - update(): 返回 CameraPose（此处代表 *camera 在世界系* 的位姿）
    """

    MIN_RANGE_M: float = 0.05

    def __init__(self, tag_pose: Optional[TagPose] = None):
        # Tag 在世界（world→tag），默认单位变换
        if tag_pose is None:
            self.tag_pose = TagPose(0, 0, 0, 0, 0, 0)
            self._T_world_tag = np.eye(4, dtype=float)
        else:
            self.set_tag_pose(tag_pose)

    def set_tag_pose(self, tag_pose: TagPose) -> None:
        """设置/更新 world→tag 的先验位姿。"""
        self.tag_pose = tag_pose
        R_w_t = project_to_so3(rpy_to_R(tag_pose.roll, tag_pose.pitch, tag_pose.yaw))
        t_w_t = np.array([tag_pose.x, tag_pose.y, tag_pose.z], float)
        self._T_world_tag = se3(R_w_t, t_w_t)

    def _world_cam_from_det(self, R_ct: np.ndarray, t_ct: np.ndarray) -> np.ndarray:
        """返回 world→cam；链乘：world→tag · tag→cam。"""
        T_ct = se3(R_ct, np.asarray(t_ct, float).reshape(3))  # tag→cam
        return self._T_world_tag @ T_ct                       # world→cam

    # --- 主入口：返回 CameraPose（相机在世界系的姿态） ---
    def update(self, det: Optional[TagDetection]) -> Optional[CameraPose]:
        if det is None:
            return None

        R_or_r = getattr(det, "pose_R", None)
        if R_or_r is None:
            R_or_r = getattr(det, "rvec", None)
        t = getattr(det, "pose_t", None)
        if t is None:
            t = getattr(det, "tvec", None)
        if R_or_r is None or t is None:
            return None

        R_ct = to_R(R_or_r)
        t_ct = np.asarray(t, float).reshape(3)
        if np.linalg.norm(t_ct) < self.MIN_RANGE_M:
            return None

        # 强制将 tag->cam 的 roll 设为 0，并保持 R in SO(3)
        R_ct = zero_roll_zyx(R_ct)

        # world→cam
        T_world_cam = self._world_cam_from_det(R_ct, t_ct)

        # 直接返回 camera 的位姿（不再涉及 car）
        x, y, z, roll, pitch, yaw = T_to_xyzrpy(T_world_cam)
        return CameraPose(x, y, z, roll, pitch, yaw)
