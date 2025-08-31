# vision/estimation/localizer.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import math
import numpy as np
import cv2  # 仅用于 Rodrigues

from ..types.tag_types import TagPose, CarPose, TagDetections, TagDetection
from ..types.camera_types import CameraPose
from .se2 import to_homogeneous_2d, invert_homogeneous_2d, mat2d_to_yaw
from .visualization import FIELD_IMG_BASE, precompose_field_map


@dataclass
class LocalizerConfig:
    smoothing_alpha: float = 0.6       # 指数平滑系数（0..1）
    default_cam_trust: float = 1.0     # 各相机默认权重
    require_pose_from_detector: bool = True  # 若为 True，要求 detection.pose_rvec/tvec 存在；否则跳过该检测


class Localizer:
    """
    多摄像头 AprilTag 融合定位器（二维版本，消费 TagDetections）
    - 输入：每路相机一次性检测得到的 TagDetections（像素/或已带rvec,tvec）
    - 输出：车体在世界系的二维位姿 CarPose(x,y,yaw) 及置信度
    """

    def __init__(
        self,
        tag_map: Dict[int, TagPose],           # 已知 Tag 的世界位姿（world ← tag）
        camera_poses: List[CameraPose],        # 车体坐标下的相机外参（car ← cam），仅用 x,y,yaw
        cam_trust: Optional[List[float]] = None,
        cfg: LocalizerConfig = LocalizerConfig(),
    ) -> None:
        if not 0.0 <= cfg.smoothing_alpha <= 1.0:
            raise ValueError("smoothing_alpha 必须在 [0, 1] 之间")
        self.tag_map = tag_map
        self.camera_poses = camera_poses
        self.cam_trust = cam_trust or [cfg.default_cam_trust] * len(camera_poses)
        assert len(self.cam_trust) == len(camera_poses), "cam_trust 长度需与 camera_poses 一致"
        self.cfg = cfg

        self.last_pose: Optional[CarPose] = None

        # 预合成地图（可选）
        self.field_image_base = precompose_field_map(
            FIELD_IMG_BASE,
            list(self.tag_map.values()),
            (0, 0),
            100,
        )
        self.composed_field_image = self.field_image_base

    # ---------- helpers ----------

    @staticmethod
    def _rvec_tvec_to_cam_tag_2d(rvec: Tuple[float, float, float],
                                 tvec: Tuple[float, float, float]) -> np.ndarray:
        """rvec,tvec(Tag→Cam) → cam←tag 的二维齐次矩阵 (3×3)"""
        rvec_np = np.array(rvec, dtype=float).reshape(3, 1)
        tvec_np = np.array(tvec, dtype=float).reshape(3)
        R_tc, _ = cv2.Rodrigues(rvec_np)               # 3×3
        yaw = float(math.atan2(R_tc[1, 0], R_tc[0, 0]))  # XY 投影
        t2 = tvec_np[:2]
        return to_homogeneous_2d(yaw, t2)  # cam ← tag

    def _weight_from_detection_2d(self, det: TagDetection, T_cam_tag: np.ndarray) -> float:
        """根据距离与置信度估算权重"""
        t = T_cam_tag[:2, 2]
        dist = float(np.linalg.norm(t))
        dist_w = 1.0 / max(dist, 0.01)
        margin = det.decision_margin
        margin_w = float(margin) if margin is not None else 1.0
        return float(dist_w * (1.0 + 0.5 * margin_w))

    def _single_camera_estimates_2d(
        self, cam_idx: int, dets: List[TagDetection]
    ) -> List[Tuple[CarPose, float]]:
        """对单相机返回多个标签的车体二维位姿候选 (CarPose, w)"""
        cam_pose = self.camera_poses[cam_idx]
        if cam_pose is None or not dets:
            return []

        # 车体 ← 相机 / 相机 ← 车体
        T_car_cam = to_homogeneous_2d(cam_pose.yaw, np.array([cam_pose.x, cam_pose.y]))
        T_cam_car = invert_homogeneous_2d(T_car_cam)

        results: List[Tuple[CarPose, float]] = []
        for det in dets:
            tag_id = getattr(det, "id", None)
            if tag_id is None:
                continue
            tag_pose = self.tag_map.get(int(tag_id))
            if tag_pose is None:
                continue

            if det.pose_rvec is None or det.pose_tvec is None:
                if self.cfg.require_pose_from_detector:
                    continue
                else:
                    # 简化版：未实现 PnP 回退，这里直接跳过
                    continue

            T_cam_tag = self._rvec_tvec_to_cam_tag_2d(det.pose_rvec, det.pose_tvec)
            # 世界 ← 标签
            T_world_tag = to_homogeneous_2d(tag_pose.yaw, np.array([tag_pose.x, tag_pose.y]))
            # 标签 ← 相机
            T_tag_cam = invert_homogeneous_2d(T_cam_tag)
            # 世界 ← 相机
            T_world_cam = T_world_tag @ T_tag_cam
            # 世界 ← 车体
            T_world_car = T_world_cam @ T_cam_car

            x = float(T_world_car[0, 2])
            y = float(T_world_car[1, 2])
            yaw = mat2d_to_yaw(T_world_car[:2, :2])

            w = self._weight_from_detection_2d(det, T_cam_tag)
            results.append((CarPose(x, y, yaw), w))

        return results

    @staticmethod
    def _fuse(cands: List[Tuple[CarPose, float]]) -> Optional[Tuple[CarPose, float]]:
        """加权融合多个 (pose, w)"""
        if not cands:
            return None
        xs = ys = sin_sum = cos_sum = ws = 0.0
        for pose, w in cands:
            xs += w * pose.x
            ys += w * pose.y
            sin_sum += w * math.sin(pose.yaw)
            cos_sum += w * math.cos(pose.yaw)
            ws += w
        if ws <= 0:
            return None
        return CarPose(xs / ws, ys / ws, math.atan2(sin_sum / ws, cos_sum / ws)), float(ws)

    # ---------- 对外主入口 ----------

    def update_from_packets(self, packets: List[TagDetections]) -> Tuple[Optional[CarPose], float]:
        """
        融合多相机一次性观测（与 VisionSystem.detect_once_all 搭配）
        Args:
            packets: 按相机序号对齐的 TagDetections 列表（缺测用 None 占位即可）
        Returns:
            (CarPose | None, confidence)
        """
        cam_estimates: List[Tuple[CarPose, float]] = []
        for cam_idx, pkt in enumerate(packets):
            if pkt is None:
                continue
            cands = self._single_camera_estimates_2d(cam_idx, pkt.detections)
            if not cands:
                continue
            fused = self._fuse(cands)
            if fused is None:
                continue
            pose, w = fused
            cam_weight = float(self.cam_trust[cam_idx])
            cam_estimates.append((pose, w * cam_weight))

        if not cam_estimates:
            return (self.last_pose, 0.0) if self.last_pose is not None else (None, 0.0)

        fused_all = self._fuse(cam_estimates)
        if fused_all is None:
            return (None, 0.0)

        pose_new, total_w = fused_all

        # 指数平滑
        if self.last_pose is None:
            pose = pose_new
        else:
            a = self.cfg.smoothing_alpha
            lx, ly, lyaw = self.last_pose.x, self.last_pose.y, self.last_pose.yaw
            x = a * pose_new.x + (1 - a) * lx
            y = a * pose_new.y + (1 - a) * ly
            sx = a * math.sin(pose_new.yaw) + (1 - a) * math.sin(lyaw)
            cx = a * math.cos(pose_new.yaw) + (1 - a) * math.cos(lyaw)
            yaw = math.atan2(sx, cx)
            pose = CarPose(x, y, yaw)

        self.last_pose = pose
        conf = float(1.0 - math.exp(-total_w)) if total_w > 0 else 0.0
        return pose, conf

    # 可选：对外提供底图（与 visualization 对齐）
    def compose_visible_field(self):
        return self.composed_field_image
