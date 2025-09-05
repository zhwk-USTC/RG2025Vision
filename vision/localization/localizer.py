# vision/estimation/localizer.py
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from ..detection.apriltag import TagDetections, TagDetection
from .se2 import to_homogeneous_2d, invert_homogeneous_2d, mat2d_to_yaw
from ..camera_node import CameraPose
from .types import TagPose, CarPose
from core.logger import logger


@dataclass
class LocalizerConfig:
    """
    配置项：
    - smoothing_alpha: 指数平滑系数 [0,1]，越大越贴近当前帧
    - cam_trust: 相机权重列表，长度需与 camera_poses 一致
    - margin_gain: 决策边距对权重的线性放大系数
    - min_range_m: 距离下限裁剪，避免 1/r 奇异
    - confidence_gamma: 置信度压缩项，conf = 1 - exp(-gamma * total_w)
    说明：
    - 在“Tag 与地面垂直（roll=pitch=0）”前提下，Tag 的高度对 2D (x,y,yaw) 无影响，因此无需配置 tag 高度。
    """
    smoothing_alpha: float = 0.6

    margin_gain: float = 0.5
    min_range_m: float = 0.05

    confidence_gamma: float = 1.0
    
    cam_poses: List[CameraPose] = field(default_factory=list)


class Localizer:
    """
    多摄像头 AprilTag 融合定位器（二维版本）。

    假设：
      - 每个 Tag 在世界系中 roll = pitch = 0（与地面垂直），yaw 与 (x,y) 已知；
      - 相机的 pitch/roll 未知也无需先验：由每帧检测的 R 已经包含，先在 3D 里求 world←cam，
        再投到地面抽取 (x, y, yaw) 参与 2D 融合。
      - Tag 高度未知且各不相同也没关系：对 2D 结果无影响（见实现）。
    """

    # ---------- lifecycle ----------

    def __init__(
        self,
        cfg: LocalizerConfig,
        tag_map: Dict[int, TagPose],            # 已知 Tag 的世界位姿（仅 x, y, yaw）
    ) -> None:
        if not (0.0 <= cfg.smoothing_alpha <= 1.0):
            raise ValueError("smoothing_alpha 必须在 [0, 1] 之间")

        self.tag_map: Dict[int, TagPose] = tag_map
        self.camera_poses: List[CameraPose] = cfg.cam_poses
        
        self.cfg = cfg

        self.last_pose: Optional[CarPose] = None

        # 预计算：T_cam_car（相机 ← 车体），外参不变时可复用（SE(2)）
        self._T_cam_car_list: List[np.ndarray] = []
        for cam_pose in self.camera_poses:
            T_car_cam = to_homogeneous_2d(cam_pose.yaw, np.array([cam_pose.x, cam_pose.y]))
            self._T_cam_car_list.append(invert_homogeneous_2d(T_car_cam))

    # ---------- helpers (pure) ----------

    @staticmethod
    def _extract_det_fields(det: TagDetection) -> Tuple[Optional[int], Optional[np.ndarray], Optional[np.ndarray], Optional[float]]:
        """
        检测器字段（默认）：
        - tag_id: int
        - pose_R: 3x3 旋转矩阵（cam ← tag）；若给的是 rvec(3,) 也会被自动转换
        - pose_t: (3,) 或 (3,1) 平移向量（cam ← tag）
        - decision_margin: float
        """
        tag_id = getattr(det, 'tag_id', None)
        R = getattr(det, 'pose_R', None)
        tvec = getattr(det, 'pose_t', None)
        margin = getattr(det, 'decision_margin', None)
        return tag_id, R, tvec, margin

    @staticmethod
    def _to_R_from_any(r_or_R) -> np.ndarray:
        """默认期望 3x3 旋转矩阵；若给的是 Rodrigues rvec(3,)/(3,1)，自动转换。"""
        if r_or_R is None:
            raise ValueError("pose_R is None")
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
        """绕世界 Z 轴的旋转矩阵（3x3）。"""
        c, s = math.cos(yaw), math.sin(yaw)
        return np.array([[c, -s, 0.0],
                         [s,  c, 0.0],
                         [0.0, 0.0, 1.0]], dtype=float)

    @staticmethod
    def _se3(R: np.ndarray, t: np.ndarray) -> np.ndarray:
        """组装 4x4 齐次矩阵。"""
        T = np.eye(4, dtype=float)
        T[:3, :3] = R
        T[:3, 3] = t.reshape(3)
        return T

    @staticmethod
    def _inv_se3(T: np.ndarray) -> np.ndarray:
        """4x4 齐次矩阵求逆。"""
        R = T[:3, :3]
        t = T[:3, 3]
        Ti = np.eye(4, dtype=float)
        Rt = R.T
        Ti[:3, :3] = Rt
        Ti[:3, 3] = -Rt @ t
        return Ti

    def _world_cam_from_det_3d(self, tag_pose: TagPose, R_ct: np.ndarray, t_ct: np.ndarray) -> np.ndarray:
        """
        用“Tag 垂直（roll=pitch=0）+ yaw 已知”的先验构造 T^W_T，
        将 Tag 的高度统一取 0（z=0），因为对 2D 结果无影响。
        然后 T^W_C = T^W_T @ (T^C_T)^{-1}，返回 4x4（SE(3)）。
        """
        R_wt = self._Rz(float(tag_pose.yaw))
        # 关键：z 取 0；即便真实高度不同，也不影响投到地面的 (x,y,yaw)
        t_wt = np.array([float(tag_pose.x), float(tag_pose.y), 0.0], dtype=float)
        T_wt = self._se3(R_wt, t_wt)

        T_ct = self._se3(R_ct, np.asarray(t_ct, dtype=float).reshape(3))
        T_tc = self._inv_se3(T_ct)

        return T_wt @ T_tc

    @staticmethod
    def _se3_to_se2_pose(T_wc: np.ndarray) -> CarPose:
        """从 4x4 的 world←cam 中抽取地面上的 (x,y,yaw)。"""
        x, y = float(T_wc[0, 3]), float(T_wc[1, 3])
        yaw = float(math.atan2(T_wc[1, 0], T_wc[0, 0]))
        return CarPose(x, y, yaw)

    def _weight_from_detection_2d(self, dist_m: float, margin: Optional[float]) -> float:
        """距离采用 1/max(||t||, eps)，并线性叠加 margin_gain * margin（若存在）。"""
        eps = max(1e-9, float(self.cfg.min_range_m))
        inv_range = 1.0 / max(float(dist_m), eps)
        m = float(margin) if margin is not None else 0.0
        return float(inv_range * (1.0 + self.cfg.margin_gain * m))

    def _single_camera_estimates_2d(
        self, cam_idx: int, dets: List[TagDetection]
    ) -> List[Tuple[CarPose, float]]:
        """
        对单相机的多标签检测，返回一组车体位姿候选 (CarPose, weight)。
        计算链：world←tag（先验：垂直 + yaw） · tag←cam（观测逆，SE3） · cam←car（外参逆，SE2）
        """
        if not dets:
            return []

        T_cam_car = self._T_cam_car_list[cam_idx]  # SE(2)
        results: List[Tuple[CarPose, float]] = []

        for det in dets:
            tag_id, R_or_rvec, tvec, margin = self._extract_det_fields(det)
            # 必须有 tag_id
            if tag_id is None:
                continue

            # 若检测器未提供位姿
            if tvec is None or R_or_rvec is None:
                logger.error(f"Localizer: detector missing pose for tag {tag_id}, skipping")
                return []


            tag_pose = self.tag_map.get(int(tag_id))
            if tag_pose is None:
                continue

            # cam ← tag (R_ct, t_ct)
            R_ct = self._to_R_from_any(R_or_rvec)
            t_ct = np.asarray(tvec, float).reshape(3)

            # world ← cam (SE3)，再投到 SE2
            T_w_c = self._world_cam_from_det_3d(tag_pose, R_ct, t_ct)
            pose_cam2d = self._se3_to_se2_pose(T_w_c)

            # world ← car = world←cam(2D) · cam←car(2D)
            T_world_cam2d = to_homogeneous_2d(pose_cam2d.yaw, np.array([pose_cam2d.x, pose_cam2d.y], dtype=float))
            T_world_car = T_world_cam2d @ T_cam_car

            x = float(T_world_car[0, 2])
            y = float(T_world_car[1, 2])
            yaw = mat2d_to_yaw(T_world_car[:2, :2])

            # 权重：用 3D t 的模长 + margin
            dist = float(np.linalg.norm(t_ct))
            w = self._weight_from_detection_2d(dist, margin)

            results.append((CarPose(x, y, yaw), w))

        return results

    @staticmethod
    def _fuse(cands: List[Tuple[CarPose, float]]) -> Optional[Tuple[CarPose, float]]:
        """对 (pose, w) 列表进行加权融合。角度用正余弦加权平均。"""
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
        """指数平滑位姿。角度通过正余弦线性插值实现平滑。"""
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
        """conf = 1 - exp(-gamma * total_w)"""
        gamma = float(self.cfg.confidence_gamma)
        return float(1.0 - math.exp(-gamma * max(0.0, float(total_weight))))

    # ---------- public API ----------

    def update_from_packets(self, packets: List[Optional[TagDetections]]) -> Tuple[Optional[CarPose], float]:
        """
        融合多相机一次性观测：
          packets: 按相机序号对齐的 TagDetections 列表（缺测可为 None）
        返回：(CarPose | None, confidence)
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
            cam_weight = 1.0
            cam_estimates.append((pose_cam, w_cam * cam_weight))

        if not cam_estimates:
            # 无观测：保持上一帧位姿但置信度为 0
            return (self.last_pose, 0.0) if self.last_pose is not None else (None, 0.0)

        fused_all = self._fuse(cam_estimates)
        if fused_all is None:
            return (None, 0.0)

        pose_new, total_w = fused_all
        pose_smoothed = self._smooth(self.last_pose, pose_new, self.cfg.smoothing_alpha)

        self.last_pose = pose_smoothed
        conf = self._confidence(total_w)
        return pose_smoothed, conf
    
    # properties
    
    def get_config(self) -> LocalizerConfig:
        """获取当前配置"""
        return self.cfg
    
