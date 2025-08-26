from typing import Dict, List, Optional, Tuple
import math
import numpy as np
from pyapriltags import Detection  # 保持与你的依赖一致

from .types import TagPose, CarPose
from ..camera import CameraPose
from .se2 import to_homogeneous_2d, invert_homogeneous_2d, mat2d_to_yaw


class Localization:
    """多摄像头 AprilTag 融合定位器（二维版本）

    Parameters
    ----------
    tag_map : Dict[int, TagPose]
        已知的 Tag 地图（world←tag）
    camera_poses : Dict[int, CameraPose]
        每个相机在车体坐标系下的二维外参（car←cam）
    cam_trust : Optional[Dict[int, float]]
        每个相机的置信权重（默认1.0）
    smoothing_alpha : float
        指数平滑系数（0..1），越大越信当前观测

    Notes
    -----
    - 输入的每个 Detection 需要包含 `pose_R(3×3)` 与 `pose_t(3,)`，
      即检测时需开启 `estimate_tag_pose=True` 并提供相机内参与 tag_size。
    - 该实现是二维近似：从 3D 姿态中只取 XY 平移与航向角。
    """

    def __init__(
        self,
        tag_map: Dict[int, TagPose],
        camera_poses: List[CameraPose],
        cam_trust: Optional[List[float]] = None,
        smoothing_alpha: float = 0.6,
    ) -> None:
        if not 0.0 <= smoothing_alpha <= 1.0:
            raise ValueError("smoothing_alpha 必须在 [0, 1] 之间")
        self.tag_map = tag_map
        self.camera_poses = camera_poses
        self.cam_trust = cam_trust or {k: 1.0 for k in range(len(camera_poses))}
        self.smoothing_alpha = float(smoothing_alpha)
        self.last_pose: Optional[CarPose] = None
        self.last_time = None

    # --- detection -> T_cam_tag ---
    @staticmethod
    def detection_to_cam_tag_2d(det: Detection) -> Optional[np.ndarray]:
        """从 Detection 提取相机←标签的二维位姿 T_cam_tag (3×3)

        Detection（pyapriltags）在 detect(..., estimate_tag_pose=True, ...) 时包含:
          - det.pose_R: (3,3)  旋转，Tag→Cam
          - det.pose_t: (3,1) 或 (3,)  平移，Tag→Cam

        我们做 2D 近似：yaw = atan2(R[1,0], R[0,0])；t = pose_t[:2]
        """
        R_tc = det.pose_R
        t_tc = det.pose_t
        if R_tc is None or t_tc is None:
            return None

        R_tc = np.asarray(R_tc, dtype=float)
        if R_tc.shape != (3, 3):
            return None

        t_tc = np.asarray(t_tc, dtype=float).ravel()
        if t_tc.size < 2:
            return None

        yaw = float(math.atan2(R_tc[1, 0], R_tc[0, 0]))  # XY 平面投影的航向角
        t2 = t_tc[:2]
        return to_homogeneous_2d(yaw, t2)  # 输出 cam ← tag

    def _weight_from_detection_2d(self, det: Detection, T_cam_tag: np.ndarray) -> float:
        """根据检测质量和距离估计权重（二维）"""
        t = T_cam_tag[:2, 2]
        dist = float(np.linalg.norm(t))
        dist_w = 1.0 / max(dist, 0.01)

        margin = det.decision_margin
        margin_w = float(margin) if margin is not None else 1.0
        return float(dist_w * (1.0 + 0.5 * margin_w))

    def _single_camera_estimates_2d(
        self, cam_idx: int, detections: List[Detection]
    ) -> List[Tuple[CarPose, float]]:
        """对单相机返回多个标签的车体二维位姿候选"""
        cam_pose = self.camera_poses[cam_idx]
        if cam_pose is None or not detections:
            return []

        # T_car_cam: 车体 ← 相机
        T_car_cam = to_homogeneous_2d(cam_pose.yaw, np.array([cam_pose.x, cam_pose.y]))
        # T_cam_car: 相机 ← 车体
        T_cam_car = invert_homogeneous_2d(T_car_cam)

        results: List[Tuple[CarPose, float]] = []
        for det in detections:
            tag_id = getattr(det, "tag_id", None)
            if tag_id is None:
                continue

            tag_pose = self.tag_map.get(int(tag_id))
            if tag_pose is None:
                continue

            T_cam_tag = self.detection_to_cam_tag_2d(det)
            if T_cam_tag is None:
                # 未开启位姿估计或失败
                continue

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
    def _fuse_candidates(
        candidates: List[Tuple[CarPose, float]]
    ) -> Optional[Tuple[CarPose, float]]:
        """给定候选 (CarPose, w) 做加权融合，返回融合结果和总权重"""
        if not candidates:
            return None
        xs = ys = sin_sum = cos_sum = ws = 0.0
        for pose, w in candidates:
            xs += w * pose.x
            ys += w * pose.y
            sin_sum += w * math.sin(pose.yaw)
            cos_sum += w * math.cos(pose.yaw)
            ws += w
        if ws <= 0:
            return None
        xf = xs / ws
        yf = ys / ws
        yawf = math.atan2(sin_sum / ws, cos_sum / ws)
        return CarPose(xf, yf, yawf), float(ws)

    def update(self, detections: List[List[Detection]]) -> Tuple[Optional[CarPose], float]:
        """融合多路相机的当前帧观测，输出 (CarPose, confidence)"""
        camera_detections = {i: det_list for i, det_list in enumerate(detections)}
        cam_estimates: List[Tuple[CarPose, float]] = []

        for cam_idx, dets in camera_detections.items():
            cand = self._single_camera_estimates_2d(cam_idx, dets)
            if not cand:
                continue
            fused = self._fuse_candidates(cand)
            if fused is None:
                continue
            pose, w = fused
            cam_weight = float(self.cam_trust[cam_idx])
            cam_estimates.append((pose, w * cam_weight))

        if not cam_estimates:
            return (self.last_pose, 0.0) if self.last_pose is not None else (None, 0.0)

        fused_all = self._fuse_candidates(cam_estimates)
        if fused_all is None:
            return (None, 0.0)

        pose_new, total_w = fused_all

        # 指数平滑
        if self.last_pose is None:
            pose = pose_new
        else:
            ax = self.smoothing_alpha
            lx, ly, lyaw = self.last_pose.x, self.last_pose.y, self.last_pose.yaw
            x = ax * pose_new.x + (1 - ax) * lx
            y = ax * pose_new.y + (1 - ax) * ly
            sx = ax * math.sin(pose_new.yaw) + (1 - ax) * math.sin(lyaw)
            cx = ax * math.cos(pose_new.yaw) + (1 - ax) * math.cos(lyaw)
            yaw = math.atan2(sx, cx)
            pose = CarPose(x, y, yaw)

        self.last_pose = pose
        conf = float(1.0 - math.exp(-total_w)) if total_w > 0 else 0.0
        return pose, conf
