# vision/localization/simple_localizer.py

from __future__ import annotations
import math
from typing import Optional, List

import cv2
import numpy as np

from .se2 import to_homogeneous_2d, invert_homogeneous_2d, mat2d_to_yaw
from ..camera_node import CameraPose
from .types import TagPose, CarPose
from ..detection.apriltag import TagDetection


class SingleTagLocalizer:
    """
    单相机·单 Tag 定位器
    - update(det) 返回：当前检测计算出的 CarPose 或 None
    - get_last_valid() 获取上一次有效检测的 CarPose
    """
    
    TAG_TO_WORLD_ALIGN = np.array([
        [ 0.0,  0.0,  1.0], 
        [-1.0,  0.0,  0.0],
        [ 0.0, -1.0,  0.0],
    ], dtype=float)

    MIN_RANGE_M: float = 0.05  # 距离下限裁剪
    def __init__(self,
                cam_pose: Optional[CameraPose] = None,
                tag_pose: Optional[TagPose] = None):
        # 默认 tag/cam 位姿：原点朝向 0
        self.cam_pose = cam_pose if cam_pose is not None else CameraPose(0.0, 0.0, 0.0)
        self.tag_pose = tag_pose if tag_pose is not None else TagPose(0.0, 0.0, 0.0)

        # cam←car (SE2) 的逆
        T_car_cam = to_homogeneous_2d(
            self.cam_pose.yaw, np.array([self.cam_pose.x, self.cam_pose.y], dtype=float)
        )
        self._T_cam_car = invert_homogeneous_2d(T_car_cam)

        self.last_valid: Optional[CarPose] = None

    # -------- 工具 --------

    @staticmethod
    def _to_R_from_any(r_or_R) -> np.ndarray:
        arr = np.asarray(r_or_R, dtype=float)
        if arr.shape == (3, 3):
            return arr
        flat = arr.reshape(-1)
        if flat.shape[0] == 3:
            R, _ = cv2.Rodrigues(flat.reshape(3, 1))
            return R
        raise ValueError(f"pose_R/pose_rvec shape invalid: {arr.shape}")

    @staticmethod
    def _Rz(yaw: float) -> np.ndarray:
        c, s = math.cos(yaw), math.sin(yaw)
        return np.array(
            [[c, -s, 0.0],
             [s,  c, 0.0],
             [0.0, 0.0, 1.0]], dtype=float
        )

    @staticmethod
    def _se3(R: np.ndarray, t: np.ndarray) -> np.ndarray:
        T = np.eye(4, dtype=float)
        T[:3, :3] = R
        T[:3, 3] = t.reshape(3)
        return T

    @staticmethod
    def _inv_se3(T: np.ndarray) -> np.ndarray:
        R = T[:3, :3]
        t = T[:3, 3]
        Ti = np.eye(4, dtype=float)
        Rt = R.T
        Ti[:3, :3] = Rt
        Ti[:3, 3] = -Rt @ t
        return Ti

    def _world_cam_from_det_3d(self, R_ct: np.ndarray, t_ct: np.ndarray) -> np.ndarray:
        R_wt = self._Rz(float(self.tag_pose.yaw)) @ self.TAG_TO_WORLD_ALIGN
        t_wt = np.array([float(self.tag_pose.x), float(self.tag_pose.y), 0.0], dtype=float)
        T_wt = self._se3(R_wt, t_wt)

        T_ct = self._se3(R_ct, np.asarray(t_ct, float).reshape(3))
        T_tc = self._inv_se3(T_ct)
        return T_wt @ T_tc

    @staticmethod
    def _se3_to_se2_pose(T_wc: np.ndarray) -> CarPose:
        x, y = float(T_wc[0, 3]), float(T_wc[1, 3])
        x = -x
        y = -y
        yaw = float(math.atan2(T_wc[1, 2], T_wc[0, 2]))
        return CarPose(x, y, yaw)

    # -------- 公共 API --------
    def update(self, det: Optional[TagDetection]) -> Optional[CarPose]:
        if det is None:
            return None

        # 显式判断 None，避免 numpy 数组触发布尔判断
        R_or_r = getattr(det, "pose_R", None)
        if R_or_r is None:
            R_or_r = getattr(det, "rvec", None)

        t = getattr(det, "pose_t", None)
        if t is None:
            t = getattr(det, "tvec", None)

        if R_or_r is None or t is None:
            return None

        R_ct = self._to_R_from_any(R_or_r)
        t_ct = np.asarray(t, dtype=float).reshape(3)

        T_w_c = self._world_cam_from_det_3d(R_ct, t_ct)
        pose_cam2d = self._se3_to_se2_pose(T_w_c)

        T_world_cam2d = to_homogeneous_2d(
            pose_cam2d.yaw, np.array([pose_cam2d.x, pose_cam2d.y], dtype=float)
        )
        T_world_car = T_world_cam2d @ self._T_cam_car

        x = float(T_world_car[0, 2])
        y = float(T_world_car[1, 2])
        yaw = mat2d_to_yaw(T_world_car[:2, :2])
        pose = CarPose(x, y, yaw)

        self.last_valid = pose
        return pose
    
    # -------- 便捷：从 detection 列表按 tag_id 选中并更新 --------
    def update_from_detections(self, detections: List[TagDetection], target_id: Optional[int] = None) -> Optional[CarPose]:
        """
        根据检测列表与可选的 target_id 选择一条 detection，并调用 update() 解算当前位姿。
        - detections: 来自 pyapriltags/pupil_apriltags 的检测结果列表
        - target_id: 需要跟踪的 tag id；若为 None，则从列表中挑选距离最近的一个
        返回：CarPose 或 None
        """
        det = self._select_detection(detections, target_id)
        if det is None:
            return None
        return self.update(det)

    # -------- 私有：从列表里挑选一个 detection --------
    @staticmethod
    def _select_detection(detections: List[TagDetection], target_id: Optional[int]) -> Optional[TagDetection]:
        if not detections:
            return None

        def get_id(d):
            return getattr(d, "tag_id", None)

        def get_dist(d) -> float:
            t = getattr(d, "pose_t", None)
            if t is None:
                t = getattr(d, "tvec", None)
            if t is None:
                return float("inf")
            arr = np.asarray(t, dtype=float).reshape(-1)
            return float(np.linalg.norm(arr)) if arr.size >= 3 else float("inf")

        # 先按 id 过滤
        cands = detections
        if target_id is not None:
            cands = [d for d in detections if get_id(d) == target_id]
            if not cands:
                return None

        # 选距离最近的
        return min(cands, key=get_dist)

    def get_last_valid(self) -> Optional[CarPose]:
        """获取上一次有效检测的位姿 (CarPose)，若没有则返回 None"""
        return self.last_valid
