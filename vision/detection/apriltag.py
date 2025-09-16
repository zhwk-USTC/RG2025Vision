from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np
import cv2
from pyapriltags import Detector, Detection
from core.logger import logger
from .types import CameraIntrinsics

TagDetection = Detection

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

    def detect(self, image: np.ndarray, intrinsics: Optional[CameraIntrinsics] = None, tag_size: Optional[float] = None) -> Optional[List[TagDetection]]:
        """进行 AprilTag 检测，并返回结果"""
        if image.ndim == 3:
            image = np.mean(image, axis=2).astype(np.uint8)
        
        estimated_pose = False
        camera_params = None
        
        # 严格检查相机内参的有效性
        if intrinsics and tag_size:
            # 检查所有必需的内参字段是否存在且不为None
            if (hasattr(intrinsics, 'fx') and intrinsics.fx is not None and
                hasattr(intrinsics, 'fy') and intrinsics.fy is not None and
                hasattr(intrinsics, 'cx') and intrinsics.cx is not None and
                hasattr(intrinsics, 'cy') and intrinsics.cy is not None):
                
                estimated_pose = True
                camera_params = (intrinsics.fx, intrinsics.fy, intrinsics.cx, intrinsics.cy)
            else:
                logger.warning("[AprilTagDetector] 相机内参不完整，跳过位姿估计")
        
        try:
            result = self.detector.detect(
                image, estimate_tag_pose=estimated_pose, camera_params=camera_params, tag_size=tag_size)
            return result
        except Exception as e:
            logger.error(f"[AprilTagDetector] 检测失败: {e}")
            return None

    @staticmethod
    def draw_overlay(img: Optional[np.ndarray], detect_result: Optional[List[Detection]]) -> Optional[np.ndarray]:
        """在图像上绘制检测结果"""
        if detect_result is None or img is None:
            return None
        if hasattr(img, 'mode'):
            img_np = np.array(img)
        else:
            img_np = np.asarray(img)
        overlay = img_np.copy()
        
        # 根据图像尺寸动态调整绘制参数
        img_height, img_width = overlay.shape[:2]
        img_diagonal = np.sqrt(img_width**2 + img_height**2)
        
        # 动态计算线条粗细（基于图像对角线长度，增加系数使线条更粗）
        line_thickness = max(2, int(img_diagonal / 200))
        
        # 动态计算字体大小和粗细（增加系数使字体更大）
        font_scale = max(0.5, img_diagonal / 400)
        font_thickness = max(3, int(img_diagonal / 200))
        
        if detect_result:
            for det in detect_result:
                corners = det.get('corners') if isinstance(
                    det, dict) else getattr(det, 'corners', None)
                tag_id = det.get('tag_id') if isinstance(
                    det, dict) else getattr(det, 'tag_id', None)
                if corners is not None:
                    pts = np.array(corners, dtype=np.int32).reshape(-1, 2)
                    cv2.polylines(overlay, [pts], isClosed=True, color=(
                        0, 255, 0), thickness=line_thickness)
                    if tag_id is not None:
                        pt = tuple(int(x) for x in corners[0])
                        cv2.putText(overlay, str(tag_id), pt,
                                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 0, 0), font_thickness)

        return overlay

    @staticmethod
    def get_result_text(detect_result: Optional[List[Detection]]) -> str:
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
    
    def update_config(self, config: TagDetectionConfig) -> None:
        """更新检测器配置"""
        self.config = config
        self.detector = Detector(
            families=config.families,
            nthreads=config.nthreads,
            quad_decimate=config.quad_decimate,
            quad_sigma=config.quad_sigma,
            refine_edges=config.refine_edges,
            decode_sharpening=config.decode_sharpening,
        )
    
        logger.info(f"[ApriltagDetector] 配置已更新: {self.config}")


class Tag36h11Detector(AprilTagDetectorBase):
    """Tag36h11 检测器"""

    def __init__(self, config: Optional[TagDetectionConfig] = None):
        if config is None:
            config = TagDetectionConfig(families='tag36h11')
        if config.families != 'tag36h11':
            raise ValueError("Invalid tag family: expected 'tag36h11'")
        super().__init__(config)
        
    def update_config(self, config: TagDetectionConfig) -> None:
        """更新检测器配置"""
        if config.families != 'tag36h11':
            raise ValueError("Invalid tag family: expected 'tag36h11'")
        super().update_config(config)
        
class Tag25h9Detector(AprilTagDetectorBase):
    """Tag25h9 检测器"""

    def __init__(self, config: Optional[TagDetectionConfig] = None):
        if config is None:
            config = TagDetectionConfig(families='tag25h9')
        if config.families != 'tag25h9':
            raise ValueError("Invalid tag family: expected 'tag25h9'")
        super().__init__(config)
        
    def update_config(self, config: TagDetectionConfig) -> None:
        """更新检测器配置"""
        if config.families != 'tag25h9':
            raise ValueError("Invalid tag family: expected 'tag25h9'")
        super().update_config(config)
