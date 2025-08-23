
"""
AprilTag 检测模块

提供 AprilTag 标签检测和位姿估计功能，支持简单检测和带位姿估计的检测模式。
"""

import json
import os
from typing import List, Dict, Tuple, Optional, Union
import numpy as np
import cv2
from pyapriltags import Detector, Detection

from core.logger import logger
from vision.camera.intrinsics import CameraIntrinsics

# 默认 tag36h11 配置参数
TAG36H11_CONFIG = {
    'nthreads': 1,
    'quad_decimate': 1.0,
    'quad_sigma': 0.0,
    'refine_edges': True,
    'decode_sharpening': 0.25,
    'debug': 0
}


class AprilTagDetector:
    """AprilTag 检测器基类"""
    
    @staticmethod
    def from_config(config: Dict) -> 'AprilTagDetector':
        """从参数字典快速创建 AprilTagDetector 实例
        
        Args:
            config: 配置参数字典
            
        Returns:
            AprilTagDetector 实例
        """
        return AprilTagDetector(
            families=config.get('families', 'tag36h11'),
            nthreads=config.get('nthreads', 1),
            quad_decimate=config.get('quad_decimate', 1.0),
            quad_sigma=config.get('quad_sigma', 0.0),
            refine_edges=config.get('refine_edges', 1),
            decode_sharpening=config.get('decode_sharpening', 0.25),
            debug=config.get('debug', 0)
        )

    def __init__(self, families: str = 'tag36h11', nthreads: int = 1, 
                 quad_decimate: float = 1.0, quad_sigma: float = 0.0, 
                 refine_edges: int = 1, decode_sharpening: float = 0.25, 
                 debug: int = 0):
        """初始化 AprilTag 检测器
        
        Args:
            families: AprilTag 标签族，默认 'tag36h11'
            nthreads: 线程数
            quad_decimate: 四边形检测降采样率
            quad_sigma: 高斯模糊参数
            refine_edges: 是否精化边缘
            decode_sharpening: 解码锐化参数
            debug: 调试级别
        """
        self.detector = Detector(
            families=families,
            nthreads=nthreads,
            quad_decimate=quad_decimate,
            quad_sigma=quad_sigma,
            refine_edges=refine_edges,
            decode_sharpening=decode_sharpening,
            debug=debug
        )

    def detect(self, image: np.ndarray, 
               camera_intrinsics: Optional[CameraIntrinsics] = None, 
               tag_size: Optional[float] = None):

        if image.ndim == 3:
            image = np.mean(image, axis=2).astype(np.uint8)
        estimated_pose = False
        camera_params = None
        if camera_intrinsics is None or tag_size is None:
            estimated_pose = False
        else:
            estimated_pose = True
            camera_params = (camera_intrinsics.fx, camera_intrinsics.fy,
                             camera_intrinsics.cx, camera_intrinsics.cy)
        result = self.detector.detect(image, estimate_tag_pose=estimated_pose, camera_params=camera_params, tag_size=tag_size)
        return result

    def draw_overlay(self, img: Union[np.ndarray, object], 
                    detect_result: Optional[List[Detection]]) -> Optional[object]:
        """在原图像上绘制 AprilTag 检测结果
        
        Args:
            img: np.ndarray 或 PIL.Image
            detect_result: 检测结果列表或字典
            
        Returns:
            PIL.Image 或 None
        """
        # 如果检测结果为 None，则返回 None
        if detect_result is None:
            return None
            
        # 转为 np.ndarray
        if hasattr(img, 'mode'):  # PIL.Image
            img_np = np.array(img)
        else:
            img_np = np.asarray(img)
            
        overlay = img_np.copy()
        
        # 只绘制 tag 的多边形框和序号
        if detect_result and isinstance(detect_result, (list, tuple)):
            for det in detect_result:
                corners = det.get('corners') if isinstance(det, dict) else getattr(det, 'corners', None)
                tag_id = det.get('tag_id') if isinstance(det, dict) else getattr(det, 'tag_id', None)
                
                if corners is not None:
                    pts = np.array(corners, dtype=np.int32).reshape(-1, 2)
                    cv2.polylines(overlay, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
                    
                    if tag_id is not None:
                        pt = tuple(int(x) for x in corners[0])
                        cv2.putText(overlay, str(tag_id), pt,
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        
        # 转为 PIL
        from PIL import Image
        overlay_pil = Image.fromarray(overlay.astype('uint8'), 'RGB')
        return overlay_pil

    def get_result_text(self, detect_result: Optional[List[Detection]]) -> str:
        """获取检测结果的文本描述
        
        Args:
            detect_result: 检测结果列表或字典
            
        Returns:
            包含所有检测到的 tag 信息的字符串
        """
        if detect_result is None:
            return "无检测结果"
        elif len(detect_result) == 0:
            return "未检测到AprilTag"
            
        result_text = []
        for r in detect_result:

            result_line = (
                'tag_id = ' + str(r.tag_id) +
                ', center = ' + f"({r.center[0]:.1f}, {r.center[1]:.1f})"
            )

            result_text.append(result_line)
                
        return "\n".join(result_text)


class Tag36h11Detector(AprilTagDetector):
    """Tag36h11 专用检测器"""
    
    @staticmethod
    def from_config(config: Dict) -> 'Tag36h11Detector':
        """从参数字典快速创建 Tag36h11Detector 实例（families强制为tag36h11）
        
        Args:
            config: 配置参数字典
            
        Returns:
            Tag36h11Detector 实例
        """
        return Tag36h11Detector(
            nthreads=config.get('nthreads', 1),
            quad_decimate=config.get('quad_decimate', 1.0),
            quad_sigma=config.get('quad_sigma', 0.0),
            refine_edges=config.get('refine_edges', 1),
            decode_sharpening=config.get('decode_sharpening', 0.25),
            debug=config.get('debug', 0)
        )

    def __init__(self, **kwargs):
        """初始化 Tag36h11 检测器，强制设置 families 为 'tag36h11'"""
        super().__init__(families='tag36h11', **kwargs)


# 配置管理
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '../.config')
os.makedirs(CONFIG_DIR, exist_ok=True)
APRILTAG_CONFIG_PATH = os.path.join(CONFIG_DIR, 'apriltag_config.json')


def save_config(path: str = APRILTAG_CONFIG_PATH) -> None:
    """保存配置到 JSON 文件
    
    Args:
        path: 配置文件路径
    """
    # 只保存 TAG36H11_CONFIG，结构为 {'tag36h11': ...}，兼容后续手动添加其他 family
    data = {'tag36h11': TAG36H11_CONFIG.copy()}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old = json.load(f)
            if isinstance(old, dict):
                for k, v in old.items():
                    if k != 'tag36h11':
                        data[k] = v
        except Exception:
            pass
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_config(path: str = APRILTAG_CONFIG_PATH) -> None:
    """从 JSON 文件读取配置并更新 TAG36H11_CONFIG
    
    Args:
        path: 配置文件路径
    """
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'tag36h11' in data:
                TAG36H11_CONFIG.clear()
                TAG36H11_CONFIG.update(data['tag36h11'])
                logger.info(f"已加载AprilTag配置: {TAG36H11_CONFIG}")
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")


def apply_config() -> None:
    """应用当前配置到 AprilTag 检测器（重建全局检测器列表）"""
    global tag36h11_detectors
    tag36h11_detectors = [
        Tag36h11Detector.from_config(TAG36H11_CONFIG) 
        for _ in range(len(tag36h11_detectors))
    ]
    logger.info(f"已应用AprilTag配置: {TAG36H11_CONFIG}")


# 初始化配置和检测器
load_config()  # 初始化时加载配置

tag36h11_detectors: List[Tag36h11Detector] = [
    Tag36h11Detector.from_config(TAG36H11_CONFIG) for _ in range(3)
]
