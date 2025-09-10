# vision/localization/simple_localizer.py

from __future__ import annotations
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
    单相机·单Tag 三维定位器（右手系：x前、y左、z上；角为弧度，ZYX）
    输入：
      - Apriltag detection 的 (R_ct, t_ct) 表示 tag→camera
      - 先验：Tag 在世界系 T_world_tag；相机在车体系 T_car_cam
    输出：
      - update(): 返回 CarPose（即 CameraPose）
      - 双边：返回 T_world_car/T_car_world/T_world_cam/T_cam_world
    """

    MIN_RANGE_M: float = 0.05

    def __init__(self,
                 cam_pose: Optional[CameraPose] = None,
                 tag_pose: Optional[TagPose] = None):
        # 相机在车体系（car→cam）
        self.cam_pose = cam_pose if cam_pose is not None else CameraPose(0, 0, 0, 0, 0, 0)
        R_car_cam = rpy_to_R(self.cam_pose.roll, self.cam_pose.pitch, self.cam_pose.yaw)
        t_car_cam = np.array([self.cam_pose.x, self.cam_pose.y, self.cam_pose.z], float)
        T_car_cam = se3(R_car_cam, t_car_cam)
        self._T_cam_car = inv_se3(T_car_cam)  # cam→car

        # Tag 在世界（world→tag）
        self.tag_pose = tag_pose if tag_pose is not None else TagPose(0, 0, 0, 0, 0, 0)
        R_w_t = rpy_to_R(self.tag_pose.roll, self.tag_pose.pitch, self.tag_pose.yaw)
        t_w_t = np.array([self.tag_pose.x, self.tag_pose.y, self.tag_pose.z], float)
        self._T_world_tag = se3(R_w_t, t_w_t)

        self._last_pose: Optional[CameraPose] = None  # CarPose == CameraPose
        self._last_T_world_car: Optional[np.ndarray] = None

    # --- 内部：由检测解出 world→cam ---
    def _world_cam_from_det(self, R_ct: np.ndarray, t_ct: np.ndarray) -> np.ndarray:
        T_ct = se3(R_ct, np.asarray(t_ct, float).reshape(3))  # tag→cam
        T_tc = inv_se3(T_ct)                                  # cam→tag
        return self._T_world_tag @ T_tc                       # world→cam

    # --- 主入口：返回 CameraPose ---
    def update(self, det: Optional[TagDetection]) -> Optional[CameraPose]:
        if det is None:
            return None

        R_or_r = getattr(det, "pose_R", None) or getattr(det, "rvec", None)
        t      = getattr(det, "pose_t", None) or getattr(det, "tvec", None)
        if R_or_r is None or t is None:
            return None

        R_ct = to_R(R_or_r)
        t_ct = np.asarray(t, float).reshape(3)
        if np.linalg.norm(t_ct) < self.MIN_RANGE_M:
            return None

        # world→car = (world→cam)·(cam→car)
        T_world_cam = self._world_cam_from_det(R_ct, t_ct)
        T_world_car = T_world_cam @ self._T_cam_car

        x, y, z, roll, pitch, yaw = T_to_xyzrpy(T_world_car)
        pose = CameraPose(x, y, z, roll, pitch, yaw)  # 注意：CarPose == CameraPose

        self._last_pose = pose
        self._last_T_world_car = T_world_car
        return pose

    # --- 从列表选择一个 detection（优先 id，否则取最近） ---
    def update_from_detections(self, detections: List[TagDetection], target_id: Optional[int] = None) -> Optional[CameraPose]:
        det = self._select_detection(detections, target_id)
        if det is None:
            return None
        return self.update(det)

    # --- 双边位置：返回四个 4×4 ---
    def update_get_bilateral(self, det: Optional[TagDetection]):
        """
        返回 (T_world_car, T_car_world, T_world_cam, T_cam_world)
        """
        if det is None:
            return None

        R_or_r = getattr(det, "pose_R", None) or getattr(det, "rvec", None)
        t      = getattr(det, "pose_t", None) or getattr(det, "tvec", None)
        if R_or_r is None or t is None:
            return None

        R_ct = to_R(R_or_r)
        t_ct = np.asarray(t, float).reshape(3)
        if np.linalg.norm(t_ct) < self.MIN_RANGE_M:
            return None

        T_world_cam = self._world_cam_from_det(R_ct, t_ct)
        T_cam_world = inv_se3(T_world_cam)
        T_world_car = T_world_cam @ self._T_cam_car
        T_car_world = inv_se3(T_world_car)

        self._last_T_world_car = T_world_car
        return T_world_car, T_car_world, T_world_cam, T_cam_world

    # --- 取上一次有效 CameraPose ---
    def get_last_valid(self) -> Optional[CameraPose]:
        return self._last_pose

    # --- 选检测 ---
    @staticmethod
    def _select_detection(detections: List[TagDetection], target_id: Optional[int]) -> Optional[TagDetection]:
        if not detections:
            return None

        def get_id(d): return getattr(d, "tag_id", None)

        def get_dist(d) -> float:
            t = getattr(d, "pose_t", None) or getattr(d, "tvec", None)
            if t is None: return float("inf")
            arr = np.asarray(t, float).reshape(-1)
            return float(np.linalg.norm(arr)) if arr.size >= 3 else float("inf")

        cands = detections if target_id is None else [d for d in detections if get_id(d) == target_id]
        if not cands:
            return None
        return min(cands, key=get_dist)
