# vision/estimation/localizer.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from ..detection.apriltag import TagDetections, TagDetection
from .se2 import to_homogeneous_2d, invert_homogeneous_2d, mat2d_to_yaw
from .visualization import FIELD_IMG_BASE, precompose_field_map
from .types import TagPose, CarPose

# =========================
# Localizer
# =========================

@dataclass
class LocalizerConfig:
    """
    配置项：
    - smoothing_alpha: 指数平滑系数 [0,1]，越大越贴近当前帧
    - default_cam_trust: 相机默认权重
    - require_pose_from_detector: 若 True 且检测未提供 rvec/tvec 则跳过
    - margin_gain: 决策边距对权重的线性放大系数
    - min_range_m: 距离下限裁剪，避免 1/r 奇异
    - enable_field_composition: 是否预合成底图（避免无用计算）
    - confidence_gamma: 置信度压缩项，conf = 1 - exp(-gamma * total_w)
    """
    smoothing_alpha: float = 0.6
    default_cam_trust: float = 1.0
    require_pose_from_detector: bool = True

    margin_gain: float = 0.5
    min_range_m: float = 0.01

    enable_field_composition: bool = True
    confidence_gamma: float = 1.0

class Localizer:
    """
    多摄像头 AprilTag 融合定位器（二维版本，消费 TagDetections）
    - 输入：每路相机一次性检测得到的 TagDetections（像素/或已带 rvec,tvec）
    - 输出：车体在世界系的二维位姿 CarPose(x,y,yaw) 及置信度（0..1）
    """

    # ---------- lifecycle ----------

    def __init__(
        self,
        tag_map: Dict[int, TagPose],            # 已知 Tag 的世界位姿（world ← tag）
        camera_poses: List[CameraPose],         # 车体坐标下的相机外参（car ← cam），仅用 x,y,yaw
        cam_trust: Optional[List[float]] = None,
        cfg: LocalizerConfig = LocalizerConfig(),
    ) -> None:
        if not (0.0 <= cfg.smoothing_alpha <= 1.0):
            raise ValueError("smoothing_alpha 必须在 [0, 1] 之间")

        self.tag_map: Dict[int, TagPose] = tag_map
        self.camera_poses: List[CameraPose] = camera_poses
        self.cam_trust: List[float] = cam_trust or [cfg.default_cam_trust] * len(camera_poses)
        if len(self.cam_trust) != len(camera_poses):
            raise ValueError("cam_trust 长度需与 camera_poses 一致")
        self.cfg = cfg

        self.last_pose: Optional[CarPose] = None

        # 可选：懒加载/禁用底图合成，避免在纯定位场景的额外开销
        self.field_image_base = None
        self.composed_field_image = None
        if self.cfg.enable_field_composition:
            self.field_image_base = precompose_field_map(
                FIELD_IMG_BASE, list(self.tag_map.values()), (0, 0), 100
            )
            self.composed_field_image = self.field_image_base

    # ---------- helpers (pure) ----------

    @staticmethod
    def _extract_det_fields(det: TagDetection) -> Tuple[Optional[int], Optional[Tuple[float, float, float]], Optional[Tuple[float, float, float]], Optional[float]]:
        """
        兼容不同检测器字段命名：
        - id / tag_id
        - pose_R 或 pose_rvec（均表示 rvec）
        - pose_t 或 pose_tvec（均表示 tvec）
        - decision_margin / score
        """
        tag_id = getattr(det, "id", None)
        if tag_id is None:
            tag_id = getattr(det, "tag_id", None)

        rvec = getattr(det, "pose_R", None)
        if rvec is None:
            rvec = getattr(det, "pose_rvec", None)

        tvec = getattr(det, "pose_t", None)
        if tvec is None:
            tvec = getattr(det, "pose_tvec", None)

        margin = getattr(det, "decision_margin", None)
        if margin is None:
            margin = getattr(det, "score", None)

        return tag_id, rvec, tvec, margin

    @staticmethod
    def _rvec_tvec_to_cam_from_tag_2d(
        rvec: Tuple[float, float, float],
        tvec: Tuple[float, float, float],
    ) -> np.ndarray:
        """
        将 rvec,tvec（Tag→Cam，OpenCV 惯例）转换为二维齐次矩阵 T_cam_tag（cam ← tag）。
        - 仅使用 XY 平面旋转分量（yaw）与平移的前两维。
        """
        rvec_np = np.array(rvec, dtype=float).reshape(3, 1)
        tvec_np = np.array(tvec, dtype=float).reshape(3)
        R_tc, _ = cv2.Rodrigues(rvec_np)  # Tag→Cam 的 3×3 旋转
        # 取 XY 平面旋转：yaw = atan2(R[1,0], R[0,0])
        yaw = float(math.atan2(R_tc[1, 0], R_tc[0, 0]))
        t2 = tvec_np[:2]
        return to_homogeneous_2d(yaw, t2)  # cam ← tag

    def _weight_from_detection_2d(self, dist_m: float, margin: Optional[float]) -> float:
        """
        根据距离与检测决策边距估算权重。
        - 距离采用 1/max(dist, eps)，并线性叠加 margin_gain * margin（若存在）。
        """
        eps = max(1e-9, float(self.cfg.min_range_m))
        inv_range = 1.0 / max(float(dist_m), eps)
        m = float(margin) if margin is not None else 0.0
        return float(inv_range * (1.0 + self.cfg.margin_gain * m))

    def _single_camera_estimates_2d(
        self, cam_idx: int, dets: List[TagDetection]
    ) -> List[Tuple[CarPose, float]]:
        """
        对单相机的多标签检测，返回一组车体位姿候选 (CarPose, weight)。
        - 计算链：world←tag（先验） · tag←cam（观测逆） · cam←car（外参逆）
        """
        cam_pose = self.camera_poses[cam_idx]
        if cam_pose is None or not dets:
            return []

        # 车体 ← 相机 / 相机 ← 车体
        T_car_cam = to_homogeneous_2d(cam_pose.yaw, np.array([cam_pose.x, cam_pose.y]))
        T_cam_car = invert_homogeneous_2d(T_car_cam)

        results: List[Tuple[CarPose, float]] = []
        for det in dets:
            tag_id, rvec, tvec, margin = self._extract_det_fields(det)
            if tag_id is None:
                continue

            tag_pose = self.tag_map.get(int(tag_id))
            if tag_pose is None:
                continue

            # 需要检测器直接给出 rvec/tvec，否则按配置决定是否忽略
            if (rvec is None) or (tvec is None):
                if self.cfg.require_pose_from_detector:
                    continue
                # 否则：此处可以扩展 PnP 回退（需 intrinsics/尺寸），当前选择跳过
                continue

            # cam ← tag
            T_cam_tag = self._rvec_tvec_to_cam_from_tag_2d(rvec, tvec)

            # world ← tag（先验）
            T_world_tag = to_homogeneous_2d(tag_pose.yaw, np.array([tag_pose.x, tag_pose.y]))

            # world ← cam = world←tag · tag←cam
            T_tag_cam = invert_homogeneous_2d(T_cam_tag)
            T_world_cam = T_world_tag @ T_tag_cam

            # world ← car = world←cam · cam←car
            T_world_car = T_world_cam @ T_cam_car

            x = float(T_world_car[0, 2])
            y = float(T_world_car[1, 2])
            yaw = mat2d_to_yaw(T_world_car[:2, :2])

            # 距离用于权重：用相机坐标系下的平移模长
            t_cam_tag_xy = T_cam_tag[:2, 2]
            dist = float(math.hypot(t_cam_tag_xy[0], t_cam_tag_xy[1]))
            w = self._weight_from_detection_2d(dist, margin)

            results.append((CarPose(x, y, yaw), w))

        return results

    @staticmethod
    def _fuse(cands: List[Tuple[CarPose, float]]) -> Optional[Tuple[CarPose, float]]:
        """
        对 (pose, w) 列表进行加权融合。角度使用正余弦加权平均保证环状连续性。
        返回 (fused_pose, total_weight)；若输入为空则返回 None。
        """
        if not cands:
            return None

        xs = ys = sin_sum = cos_sum = ws = 0.0
        for pose, w in cands:
            ws += w
            xs += w * pose.x
            ys += w * pose.y
            sin_sum += w * math.sin(pose.yaw)
            cos_sum += w * math.cos(pose.yaw)

        if ws <= 0.0:
            return None

        yaw = math.atan2(sin_sum, cos_sum)
        return CarPose(xs / ws, ys / ws, yaw), float(ws)

    @staticmethod
    def _smooth(prev: Optional[CarPose], new: CarPose, alpha: float) -> CarPose:
        """
        指数平滑位姿。角度通过正余弦线性插值实现平滑。
        """
        if prev is None:
            return new

        a = float(alpha)
        x = a * new.x + (1 - a) * prev.x
        y = a * new.y + (1 - a) * prev.y

        sx = a * math.sin(new.yaw) + (1 - a) * math.sin(prev.yaw)
        cx = a * math.cos(new.yaw) + (1 - a) * math.cos(prev.yaw)
        yaw = math.atan2(sx, cx)
        return CarPose(x, y, yaw)

    def _confidence(self, total_weight: float) -> float:
        """
        将总权重压缩为 [0,1] 的置信度。
        保持与原实现兼容：conf = 1 - exp(-gamma * total_w)
        """
        gamma = float(self.cfg.confidence_gamma)
        return float(1.0 - math.exp(-gamma * max(0.0, float(total_weight))))

    # ---------- public API ----------

    def update_from_packets(self, packets: List[Optional[TagDetections]]) -> Tuple[Optional[CarPose], float]:
        """
        融合多相机一次性观测（与 VisionSystem.detect_once_all 搭配）
        Args:
            packets: 按相机序号对齐的 TagDetections 列表（缺测可为 None）
        Returns:
            (CarPose | None, confidence)
        """
        cam_estimates: List[Tuple[CarPose, float]] = []

        for cam_idx, pkt in enumerate(packets):
            if pkt is None:
                continue

            cands = self._single_camera_estimates_2d(cam_idx, pkt)
            if not cands:
                continue

            fused_cam = self._fuse(cands)
            if fused_cam is None:
                continue

            pose_cam, w_cam = fused_cam
            cam_weight = float(self.cam_trust[cam_idx])
            cam_estimates.append((pose_cam, w_cam * cam_weight))

        if not cam_estimates:
            # 若完全无观测，则保持上一次的位姿但置信度为 0
            return (self.last_pose, 0.0) if self.last_pose is not None else (None, 0.0)

        fused_all = self._fuse(cam_estimates)
        if fused_all is None:
            return (None, 0.0)

        pose_new, total_w = fused_all
        pose_smoothed = self._smooth(self.last_pose, pose_new, self.cfg.smoothing_alpha)

        self.last_pose = pose_smoothed
        conf = self._confidence(total_w)
        return pose_smoothed, conf

    # 可选：对外提供底图（与 visualization 对齐）
    def compose_visible_field(self):
        return self.composed_field_image
