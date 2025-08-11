
"""
AprilTag 检测模块

提供 AprilTag 标签检测和位姿估计功能，支持简单检测和带位姿估计的检测模式。
"""

import json
import os
from typing import List, Dict, Tuple, Optional, Union

import numpy as np
from pyapriltags import Detector

from core.logger import logger

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

    def detect_with_pose(self, image: np.ndarray, 
                        camera_params: Tuple[float, float, float, float], 
                        tag_size: float = 0.16) -> List[Dict]:
        """检测 AprilTag 并计算相对摄像头的位姿
        
        Args:
            image: 输入灰度图像 (np.ndarray, uint8)
            camera_params: (fx, fy, cx, cy) 摄像头内参
            tag_size: tag实际边长(m)，默认16cm
            
        Returns:
            检测结果列表，每项包含：
            {
                'tag_id': int,
                'center': (x, y),  # 像素坐标
                'corners': [(x1,y1), (x2,y2), (x3,y3), (x4,y4)],  # 四个角点
                'distance': float,  # 距离(m)
                'bearing': float,   # 方位角(rad)，相对摄像头坐标系
                'confidence': float  # 检测置信度
            }
            
        Raises:
            ValueError: 如果camera_params为None或格式不正确
            ValueError: 如果tag_size无效
        """
        # 参数验证
        if camera_params is None:
            raise ValueError("camera_params 不能为 None，必须提供摄像头内参 (fx, fy, cx, cy)")
        
        if not isinstance(camera_params, (tuple, list)) or len(camera_params) != 4:
            raise ValueError("camera_params 必须是包含4个元素的元组或列表: (fx, fy, cx, cy)")
        
        fx, fy, cx, cy = camera_params
        if not all(isinstance(param, (int, float)) and param > 0 for param in [fx, fy]):
            raise ValueError("焦距参数 fx, fy 必须是正数")
        
        if not all(isinstance(param, (int, float)) for param in [cx, cy]):
            raise ValueError("光心参数 cx, cy 必须是数值")
        
        if not isinstance(tag_size, (int, float)) or tag_size <= 0:
            raise ValueError("tag_size 必须是正数")
        
        if image.ndim == 3:
            image = np.mean(image, axis=2).astype(np.uint8)
        
        # 确保 camera_params 是正确的元组格式
        camera_params_tuple: Tuple[float, float, float, float] = (
            float(camera_params[0]), float(camera_params[1]), 
            float(camera_params[2]), float(camera_params[3])
        )
            
        # 使用 pyapriltags 进行检测
        results = self.detector.detect(
            image,
            estimate_tag_pose=True,  # 始终启用位姿估计
            camera_params=camera_params_tuple,
            tag_size=tag_size
        )
        
        # 转换为标准格式并计算位姿
        formatted_results = []
        for result in results:
            # 基本信息
            tag_data = {
                'tag_id': result.tag_id,
                'center': tuple(result.center),
                'corners': [tuple(corner) for corner in result.corners],
                'confidence': max(0.0, min(1.0, 1.0 - result.hamming / 5.0))  # 汉明距离越小置信度越高
            }
            
            # 计算相对位姿 - 只使用精确方法
            fx, fy, cx, cy = camera_params_tuple
            
            # 优先使用 pyapriltags 的 pose 估计结果
            if (hasattr(result, 'pose_R') and hasattr(result, 'pose_t') and 
                result.pose_t is not None):
                # 从变换矩阵中提取距离和方位角
                translation = result.pose_t.flatten()
                distance = np.linalg.norm(translation)
                
                # 计算水平方位角（相对摄像头z轴的角度）
                bearing = np.arctan2(translation[0], translation[2])
                
                tag_data['distance'] = distance
                tag_data['bearing'] = bearing
            else:
                # 使用基于像素坐标和标签大小的精确估计
                distance, bearing = self._estimate_pose_from_pixels(
                    tuple(result.center), 
                    [tuple(corner) for corner in result.corners], 
                    camera_params_tuple, 
                    tag_size
                )
                tag_data['distance'] = distance
                tag_data['bearing'] = bearing
            
            formatted_results.append(tag_data)
        
        return formatted_results
    
    def _estimate_pose_from_pixels(self, center: Tuple[float, float], 
                                  corners: List[Tuple[float, float]], 
                                  camera_params: Tuple[float, float, float, float], 
                                  tag_size: float) -> Tuple[float, float]:
        """基于像素坐标和摄像头内参估计距离和方位角
        
        Args:
            center: (x, y) 中心像素坐标
            corners: [(x1,y1), ...] 四个角点
            camera_params: (fx, fy, cx, cy)
            tag_size: 标签实际尺寸(m)
            
        Returns:
            (distance, bearing): 距离(m)和方位角(rad)
        """
        fx, fy, cx, cy = camera_params
        center_x, center_y = center
        
        # 计算标签在图像中的像素尺寸
        corner_array = np.array(corners)
        edge_lengths = []
        for i in range(4):
            p1 = corner_array[i]
            p2 = corner_array[(i + 1) % 4]
            length = np.linalg.norm(p2 - p1)
            edge_lengths.append(length)
        
        avg_edge_length_pixels = np.mean(edge_lengths)
        
        # 估计距离：distance = tag_size_real * focal_length / tag_size_pixels
        distance = float(tag_size * fx / avg_edge_length_pixels)
        
        # 计算方位角：基于中心点相对光心的位置
        norm_x = (center_x - cx) / fx
        bearing = float(np.arctan2(norm_x, 1.0))  # 水平方向的角度
        
        return distance, bearing
    
    def detect_simple(self, image: np.ndarray) -> List[Dict]:
        """简单检测方法，不进行位姿估计
        
        Args:
            image: 输入灰度图像 (np.ndarray, uint8)
            
        Returns:
            检测结果列表，每项包含：
            {
                'tag_id': int,
                'center': (x, y),  # 像素坐标
                'corners': [(x1,y1), (x2,y2), (x3,y3), (x4,y4)],  # 四个角点
                'confidence': float,  # 检测置信度
            }
        """
        if image.ndim == 3:
            image = np.mean(image, axis=2).astype(np.uint8)
            
        results = self.detector.detect(image)
        
        # 转换为自定义格式
        formatted_results = []
        for result in results:
            # 基本信息
            tag_data = {
                'tag_id': result.tag_id,
                'center': tuple(result.center),
                'corners': [tuple(corner) for corner in result.corners],
                'confidence': max(0.0, min(1.0, 1.0 - result.hamming / 5.0))
            }
            
            formatted_results.append(tag_data)
        
        return formatted_results

    def detect(self, image: np.ndarray, 
               camera_params: Optional[Tuple[float, float, float, float]] = None, 
               tag_size: Optional[float] = None) -> List[Dict]:
        """检测 AprilTag 并返回自定义格式的结果
        
        Args:
            image: 输入灰度图像 (np.ndarray, uint8)  
            camera_params: (fx, fy, cx, cy) 或 None
            tag_size: tag实际边长(m)，用于姿态估计
            
        Returns:
            自定义格式的检测结果列表
        """
        if camera_params is None or tag_size is None:
            # 如果没有提供相机参数或标签大小，则使用简单检测方法
            return self.detect_simple(image)
        return self.detect_with_pose(image, camera_params, tag_size)

    def draw_overlay(self, img: Union[np.ndarray, object], 
                    detect_result: Optional[List[Dict]]) -> Optional[object]:
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
            
        try:
            import cv2
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as e:
            logger.warning(f"缺少必需的库: {e}")
            return None
            
        # 转为 np.ndarray
        if hasattr(img, 'mode'):  # PIL.Image
            img_np = np.array(img)
        else:
            img_np = np.asarray(img)
        
        if not isinstance(img_np, np.ndarray):
            logger.warning("输入图像类型不支持")
            return None
            
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

    def get_result_text(self, detect_result: Optional[List[Dict]]) -> str:
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
            if isinstance(r, dict):
                tag_id = r.get('tag_id', '未知')
                center = r.get('center', (0, 0))
                distance = r.get('distance', None)
                confidence = r.get('confidence', None)
                
                result_line = f"ID: {tag_id}, Center: {center[0]:.1f}, {center[1]:.1f}"
                if confidence is not None:
                    result_line += f", Confidence: {confidence:.2f}"
                if distance is not None:
                    result_line += f", Distance: {distance:.2f}m"
                    
                result_text.append(result_line)
            else:
                result_text.append(str(r))
                
        return "\n".join(result_text)

    def _format_result(self, r) -> Dict:
        """将 pupil_apriltags 的 Detection 对象转换为字典格式
        
        Args:
            r: Detection 对象
            
        Returns:
            格式化后的检测结果字典
        """
        d = {
            'tag_id': r.tag_id,
            'family': r.tag_family.decode() if hasattr(r.tag_family, 'decode') else str(r.tag_family),
            'center': tuple(r.center),
            'corners': [tuple(c) for c in r.corners],
            'decision_margin': r.decision_margin,
        }
        
        if hasattr(r, 'pose_t') and r.pose_t is not None:
            d['pose_t'] = tuple(r.pose_t.flatten())
        if hasattr(r, 'pose_R') and r.pose_R is not None:
            d['pose_R'] = r.pose_R.tolist()
            
        return d


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
                logger.info(f"已加载AprilTag配置: {TAG36H11_CONFIG}", notify_gui=False)
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
