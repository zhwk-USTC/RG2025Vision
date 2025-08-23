from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import math
from typing import Any
from pyapriltags import Detection


@dataclass
class CameraPose:
    """摄像头在小车坐标系下的二维外参（x, y, yaw）

    - x, y: 平移（m）
    - yaw: 旋转角度（弧度）
    """
    x: float
    y: float
    yaw: float
    

@dataclass
class TagPose:
    """AprilTag 在场地（world）坐标系中的二维位姿（x, y, yaw）

    - x, y: 标签中心位置（m）
    - yaw: 旋转角度（弧度）
    """
    id: int
    x: float
    y: float
    yaw: float


@dataclass
class CarPose:
    """小车二维位姿 (x, y, yaw)，单位米/弧度"""
    x: float
    y: float
    yaw: float


# ====== 2D SE2 工具 ======
def to_homogeneous_2d(yaw: float, t: np.ndarray) -> np.ndarray:
    """构造 3x3 二维齐次变换矩阵"""
    c, s = math.cos(yaw), math.sin(yaw)
    T = np.eye(3, dtype=float)
    T[0, 0] = c
    T[0, 1] = -s
    T[1, 0] = s
    T[1, 1] = c
    T[0:2, 2] = np.asarray(t, dtype=float).reshape(2)
    return T


def invert_homogeneous_2d(T: np.ndarray) -> np.ndarray:
    """计算 3x3 二维齐次矩阵的逆"""
    R = T[:2, :2]
    t = T[:2, 2]
    Tinv = np.eye(3, dtype=float)
    Tinv[:2, :2] = R.T
    Tinv[:2, 2] = -R.T @ t
    return Tinv


def mat2d_to_yaw(R: np.ndarray) -> float:
    """从二维旋转矩阵中提取 yaw（radians）"""
    return float(math.atan2(R[1, 0], R[0, 0]))


# ====== Localization 核心 ======
class Localization:
    """多摄像头 AprilTag 融合定位器（二维版本）

    用法示例:
        loc = Localization(tag_map, camera_poses)
        pose, conf = loc.update(camera_detections)

    - tag_map: dict[tag_id] -> TagPose
    - camera_poses: dict[cam_idx] -> CameraPose (camera -> car transform)
    - camera_detections: dict[cam_idx] -> list of Detection (pyapriltags)
    """

    def __init__(self, tag_map: Dict[int, TagPose], camera_poses: Dict[int, CameraPose],
                 cam_trust: Optional[Dict[int, float]] = None, smoothing_alpha: float = 0.6):
        self.tag_map = tag_map
        self.camera_poses = camera_poses
        self.cam_trust = cam_trust or {k: 1.0 for k in camera_poses.keys()}
        self.smoothing_alpha = float(smoothing_alpha)
        # 状态
        self.last_pose = None
        self.last_time = None

    # --- detection -> T_cam_tag ---
    @staticmethod
    def detection_to_cam_tag_2d(det: Any) -> Optional[np.ndarray]:
        """从 pyapriltags Detection 提取相机到标签的二维齐次位姿 T_cam_tag (3x3)

        要求 det 提供 pose_yaw (float) 和 pose_t (2,)
        返回 3x3 矩阵或 None
        """
        if det is None:
            return None
        # 包容不同属性名
        yaw = getattr(det, 'pose_yaw', None)
        t = getattr(det, 'pose_t', None)
        if yaw is None or t is None:
            yaw = det.get('pose_yaw') if isinstance(det, dict) else yaw
            t = det.get('pose_t') if isinstance(det, dict) else t
        if yaw is None or t is None:
            return None
        t = np.asarray(t, dtype=float).reshape(2)
        return to_homogeneous_2d(float(yaw), t)

    def _weight_from_detection_2d(self, det: Any, T_cam_tag: np.ndarray) -> float:
        """根据检测质量和距离估计权重（二维）"""
        t = T_cam_tag[:2, 2]
        dist = float(np.linalg.norm(t))
        dist_w = 1.0 / max(dist, 0.01)
        # decision margin if available
        margin = getattr(det, 'decision_margin', None)
        if margin is None:
            margin = det.get('decision_margin') if isinstance(det, dict) else None
        margin_w = float(margin) if margin is not None else 1.0
        w = dist_w * (1.0 + 0.5 * margin_w)
        return float(w)

    def _single_camera_estimates_2d(self, cam_idx: int, detections: List[Any]) -> List[Tuple[CarPose, float]]:
        """对单相机返回多个标签的车体二维位姿候选
        返回列表 (CarPose, weight)
        """
        cam_pose = self.camera_poses.get(cam_idx)
        if cam_pose is None or detections is None:
            return []
        # 构造 T_car_cam
        T_car_cam = to_homogeneous_2d(cam_pose.yaw, np.array([cam_pose.x, cam_pose.y]))
        T_cam_car = invert_homogeneous_2d(T_car_cam)

        results = []
        for det in detections:
            # extract tag id
            tag_id = getattr(det, 'tag_id', None)
            if tag_id is None and isinstance(det, dict):
                tag_id = det.get('tag_id')
            if tag_id is None:
                continue
            tag_pose = self.tag_map.get(int(tag_id))
            if tag_pose is None:
                continue
            T_cam_tag = self.detection_to_cam_tag_2d(det)
            if T_cam_tag is None:
                continue
            # T_world_tag
            T_world_tag = to_homogeneous_2d(tag_pose.yaw, np.array([tag_pose.x, tag_pose.y]))
            # T_world_cam = T_world_tag * T_tag_cam (T_tag_cam = inv(T_cam_tag))
            T_tag_cam = invert_homogeneous_2d(T_cam_tag)
            T_world_cam = T_world_tag @ T_tag_cam
            # T_world_car = T_world_cam * T_cam_car
            T_world_car = T_world_cam @ T_cam_car
            x = float(T_world_car[0, 2])
            y = float(T_world_car[1, 2])
            yaw = mat2d_to_yaw(T_world_car[:2, :2])
            w = self._weight_from_detection_2d(det, T_cam_tag)
            results.append((CarPose(x, y, yaw), w))
        return results

    def _fuse_candidates(self, candidates: List[Tuple[CarPose, float]]) -> Optional[Tuple[CarPose, float]]:
        """给定候选 (CarPose, w) 做加权融合，返回融合结果和总权重"""
        if not candidates:
            return None
        xs, ys, sin_sum, cos_sum, ws = 0.0, 0.0, 0.0, 0.0, 0.0
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
        return (CarPose(xf, yf, yawf), float(ws))

    def update(self, detections: List[List[Detection]]) -> Tuple[Optional[CarPose], float]:
        """主接口：输入多路摄像头的 apriltag 检测结果，返回融合后的 CarPose 和置信度（二维）

        detections: List[List[Detection]]，每个元素为一个摄像头的检测结果列表
        返回: (CarPose, confidence)
        """
        camera_detections = {i: det_list for i, det_list in enumerate(detections)}
        cam_estimates = []  # list of (CarPose, weight * cam_trust)
        for cam_idx, dets in camera_detections.items():
            cand = self._single_camera_estimates_2d(cam_idx, dets)
            if not cand:
                continue
            fused = self._fuse_candidates(cand)
            if fused is None:
                continue
            pose, w = fused
            cam_weight = float(self.cam_trust.get(cam_idx, 1.0))
            cam_estimates.append((pose, w * cam_weight))

        if not cam_estimates:
            # 无观测，仅返回预测（平滑器）或 None
            return (self.last_pose, 0.0) if self.last_pose is not None else (None, 0.0)

        # 融合所有相机
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
        # confidence 由总权重归一化（可按需要缩放），这里返回简单的 0..1 值
        conf = float(1.0 - math.exp(-total_w)) if total_w > 0 else 0.0
        return (pose, conf)

