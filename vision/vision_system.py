import asyncio
import time
import numpy as np
from typing import Dict, Iterable, List, Optional, Tuple, Union, Literal
from dataclasses import dataclass, field
import threading

from core.logger import logger
from .camera import Camera, scan_cameras, CameraConfig
from .detection.apriltag import TagDetection, TagDetectionConfig, Tag36h11Detector, Tag25h9Detector
from .detection.hsv import HSVDetector, HSVDetectConfig, HSVDetection
from .detection.types import CameraIntrinsics
from .localization.types import TagPose, CameraPose
from .localization.simple_localizer import SingleTagLocalizer

CAM_KEY_TYPE = Literal["front", "left"]

@dataclass
class VisionSystemConfig:
    # key: cam key, value: cam config dict
    cameras: Dict[str, CameraConfig] = field(default_factory=dict)
    camera_intrinsics: Dict[str, Optional[CameraIntrinsics]] = field(
        default_factory=dict)  # 存储相机内参等元信息
    tag36h11_detector: TagDetectionConfig = TagDetectionConfig(
        families='tag36h11')
    tag25h9_detector: TagDetectionConfig = TagDetectionConfig(
        families='tag25h9')
    hsv_detector: HSVDetectConfig = HSVDetectConfig()

class VisionSystem:
    def __init__(
        self,
        VisionSystemConfig: Optional[VisionSystemConfig] = None,
    ) -> None:

        # ---------- Cameras ----------
        self._cameras: Dict[str, Camera] = {}
        self._camera_intrinsics: Dict[str, Optional[CameraIntrinsics]] = {}
        self._latest_frames: Dict[str, Optional[np.ndarray]] = {}
        # ---------- Detection ----------
        self._tag36h11_detector: Tag36h11Detector = Tag36h11Detector()
        self._tag25h9_detector: Tag25h9Detector = Tag25h9Detector()
        self._hsv_detector: HSVDetector = HSVDetector()
        self._localizer: SingleTagLocalizer = SingleTagLocalizer()

        scan_cameras()
        try:
            if VisionSystemConfig is not None:
                # 加载已有相机配置
                cam_configs = VisionSystemConfig.cameras
                for key, cam_config in cam_configs.items():
                    cam = Camera(cam_config)
                    self._cameras[key] = cam
                    logger.info(f"[VisionSystem] 添加相机 {key}: {cam.name}")

                # 检测器配置
                tag36h11_detector_config = VisionSystemConfig.tag36h11_detector
                self._tag36h11_detector = Tag36h11Detector(
                    tag36h11_detector_config)
                logger.info(f"[VisionSystem] 添加 36h11 检测器")
                
                tag25h9_detector_config = VisionSystemConfig.tag25h9_detector
                self._tag25h9_detector = Tag25h9Detector(
                    tag25h9_detector_config)
                logger.info(f"[VisionSystem] 添加 25h9 检测器")

                self._hsv_detector = HSVDetector(
                    VisionSystemConfig.hsv_detector)
                logger.info(f"[VisionSystem] 添加 HSV 检测器")
                self._camera_intrinsics = VisionSystemConfig.camera_intrinsics

            # —— 兜底：确保 CAM_KEY_TYPE 都存在；没有就创建默认相机 ——
            required_keys = {"front", "left"}
            for k in required_keys:
                if k not in self._cameras:
                    default_cfg = CameraConfig(
                        index=-1, width=1920, height=1080, fps=30.0)
                    self._cameras[k] = Camera(default_cfg)
                    self._camera_intrinsics.setdefault(k, None)  # 预留元信息字典
                    logger.info(f"[VisionSystem] 自动创建默认相机 {k}")
        except Exception as e:
            logger.error(f"[VisionSystem] 初始化异常: {e}")
        else:
            logger.info(f"[VisionSystem] 初始化完成")

    # ---------------- 基本操作 ----------------
    def read_frame(self, key: CAM_KEY_TYPE) -> Optional[np.ndarray]:
        cam = self._cameras.get(key)
        if cam is None:
            logger.error(f"[VisionSystem] read_frame 未找到相机 {key}")
            return None

        frame = cam.read_frame()
        self._latest_frames[key] = frame
        return frame

    def get_camera_intrinsics(self, key: CAM_KEY_TYPE) -> Optional[CameraIntrinsics]:
        intrinsics = self._camera_intrinsics.get(key)
        return intrinsics

    def get_latest_frame(self, key: CAM_KEY_TYPE) -> Optional[np.ndarray]:
        return self._latest_frames.get(key)

    def detect_tag36h11(self, frame: Optional[np.ndarray], intrinsics: Optional[CameraIntrinsics], tag_size: Optional[float]) -> Optional[List[TagDetection]]:
        if frame is None:
            logger.error(f"[VisionSystem] detect_tag36h11 输入帧为空")
            return None
        detector = self._tag36h11_detector

        result = detector.detect(
            image=frame, intrinsics=intrinsics, tag_size=tag_size)
        return result
    
    def detect_tag25h9(self, frame: Optional[np.ndarray], intrinsics: Optional[CameraIntrinsics], tag_size: Optional[float]) -> Optional[List[TagDetection]]:
        if frame is None:
            logger.error(f"[VisionSystem] detect_tag25h9 输入帧为空")
            return None
        detector = self._tag25h9_detector

        result = detector.detect(
            image=frame, intrinsics=intrinsics, tag_size=tag_size)
        return result
    
    def detect_hsv(self, frame: Optional[np.ndarray]) -> Optional[List[HSVDetection]]:
        if frame is None:
            logger.error(f"[VisionSystem] detect_hsv 输入帧为空")
            return None
        detector = self._hsv_detector
        result = detector.detect(frame)
        return result

    def locate_from_tag(self, detection: TagDetection) -> Optional[CameraPose]:
        return self._localizer.update(detection)

    def shutdown(self) -> None:
        for key, cam in self._cameras.items():
            if cam.connected:
                cam.disconnect()
                logger.info(f"[VisionSystem] 关闭相机 {key}")
    # ---------------- 配置 ----------------

    def get_config(self) -> VisionSystemConfig:
        cams = {k: cam.get_config() for k, cam in self._cameras.items()}
        tag36h11_detector = self._tag36h11_detector.get_config()
        hsv_detector = self._hsv_detector.get_config()
        return VisionSystemConfig(
            cameras=cams,
            camera_intrinsics=self._camera_intrinsics,
            tag36h11_detector=tag36h11_detector,
            tag25h9_detector=self._tag25h9_detector.get_config(),
            hsv_detector=hsv_detector,
        )
