import json
import os
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np
import cv2
from pyapriltags import Detector, Detection
from core.logger import logger
from ..camera_node.types import CameraIntrinsics

TagDetection = Detection

TagDetections = List[TagDetection]

@dataclass(slots=True)
class TagDetectionConfig:
    families: str = 'tag36h11'
    nthreads: int = 1
    quad_decimate: float = 2.0
    quad_sigma: float = 0.0
    refine_edges: int = 1
    decode_sharpening: float = 0.25
    debug: int = 0

# 默认配置（支持多个标签种类）
DEFAULT_CONFIG = {
    'tag36h11': {
        'nthreads': 1,
        'quad_decimate': 1.0,
        'quad_sigma': 0.0,
        'refine_edges': True,
        'decode_sharpening': 0.25,
        'debug': 0
    }
}

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '../.config')
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(CONFIG_DIR, 'apriltag_config.json')


class AprilTagDetectorBase:
    """AprilTag 检测器基类"""

    def __init__(self, config: TagDetectionConfig):
        self.config = config
        self.detector = Detector(
            families=config.families,
            nthreads=config.nthreads,
            quad_decimate=config.quad_decimate,
            quad_sigma=config.quad_sigma,
            refine_edges=config.refine_edges,
            decode_sharpening=config.decode_sharpening,
        )

    def detect(self, image: np.ndarray, camera_intrinsics: Optional[CameraIntrinsics] = None, tag_size: Optional[float] = None) -> Optional[TagDetections]:
        """进行 AprilTag 检测，并返回结果"""
        if image.ndim == 3:
            image = np.mean(image, axis=2).astype(np.uint8)
        estimated_pose = False
        camera_params = None
        if camera_intrinsics and tag_size:
            estimated_pose = True
            camera_params = (camera_intrinsics.fx, camera_intrinsics.fy,
                             camera_intrinsics.cx, camera_intrinsics.cy)
        result = self.detector.detect(
            image, estimate_tag_pose=estimated_pose, camera_params=camera_params, tag_size=tag_size)
        return result

    @staticmethod
    def draw_overlay(img: Union[np.ndarray, object], detect_result: Optional[List[Detection]]) -> Optional[object]:
        """在图像上绘制检测结果"""
        if detect_result is None:
            return None
        if hasattr(img, 'mode'):
            img_np = np.array(img)
        else:
            img_np = np.asarray(img)
        overlay = img_np.copy()
        if detect_result:
            for det in detect_result:
                corners = det.get('corners') if isinstance(
                    det, dict) else getattr(det, 'corners', None)
                tag_id = det.get('tag_id') if isinstance(
                    det, dict) else getattr(det, 'tag_id', None)
                if corners is not None:
                    pts = np.array(corners, dtype=np.int32).reshape(-1, 2)
                    cv2.polylines(overlay, [pts], isClosed=True, color=(
                        0, 255, 0), thickness=2)
                    if tag_id is not None:
                        pt = tuple(int(x) for x in corners[0])
                        cv2.putText(overlay, str(tag_id), pt,
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        from PIL import Image
        overlay_pil = Image.fromarray(overlay.astype('uint8'), 'RGB')
        return overlay_pil

    def get_result_text(self, detect_result: Optional[List[Detection]]) -> str:
        """获取检测结果的文本描述"""
        if detect_result is None:
            return "无检测结果"
        elif len(detect_result) == 0:
            return "未检测到AprilTag"
        result_text = []
        for r in detect_result:
            result_line = f'tag_id = {r.tag_id}, center = ({r.center[0]:.1f}, {r.center[1]:.1f})'
            result_text.append(result_line)
        return "\n".join(result_text)

    def get_config(self) -> TagDetectionConfig:
        """获取检测器的配置"""
        return self.config


class Tag36h11Detector(AprilTagDetectorBase):
    """Tag36h11 检测器"""

    def __init__(self, config: TagDetectionConfig):
        if config.families != 'tag36h11':
            raise ValueError("Invalid tag family: expected 'tag36h11'")
        super().__init__(config)
        
    def update_config(self, config: TagDetectionConfig) -> None:
        """更新检测器配置"""
        if config.families != 'tag36h11':
            raise ValueError("Invalid tag family: expected 'tag36h11'")
        self.config = config
        self.detector = Detector(
            families=config.families,
            nthreads=config.nthreads,
            quad_decimate=config.quad_decimate,
            quad_sigma=config.quad_sigma,
            refine_edges=config.refine_edges,
            decode_sharpening=config.decode_sharpening,
        )
        logger.info(f"[Tag36h11Detector] 配置已更新: {self.config}")
