
from core.logger import logger
import json
import os
import numpy as np
from pyapriltags import Detector
tag36h11_config = {
    'nthreads': 1,
    'quad_decimate': 1.0,
    'quad_sigma': 0.0,
    'refine_edges': True,
    'decode_sharpening': 0.25,
    'debug': 0
}


class AprilTagDetector:
    @staticmethod
    def from_config(config: dict):
        """从参数dict快速创建AprilTagDetector实例"""
        return AprilTagDetector(
            families=config.get('families', 'tag36h11'),
            nthreads=config.get('nthreads', 1),
            quad_decimate=config.get('quad_decimate', 1.0),
            quad_sigma=config.get('quad_sigma', 0.0),
            refine_edges=config.get('refine_edges', 1),
            decode_sharpening=config.get('decode_sharpening', 0.25),
            debug=config.get('debug', 0)
        )

    def __init__(self, families='tag36h11', nthreads=1, quad_decimate=1.0, quad_sigma=0.0, refine_edges=1, decode_sharpening=0.25, debug=0):
        self.detector = Detector(
            families=families,
            nthreads=nthreads,
            quad_decimate=quad_decimate,
            quad_sigma=quad_sigma,
            refine_edges=refine_edges,
            decode_sharpening=decode_sharpening,
            debug=debug
        )

    def detect(self, image, camera_params=None, tag_size=None):
        """
        image: 输入灰度图像 (np.ndarray, uint8)
        camera_params: (fx, fy, cx, cy) 或 None
        tag_size: tag实际边长(m)，用于姿态估计
        返回: 检测结果列表，每项为dict
        """
        if image.ndim == 3:
            image = np.mean(image, axis=2).astype(np.uint8)
        results = self.detector.detect(
            image,
            estimate_tag_pose=(
                camera_params is not None and tag_size is not None),
            camera_params=camera_params,
            tag_size=tag_size
        )
        return results

    def draw_overlay(self, img, detect_result):
        """
        在原图像上绘制AprilTag检测结果。
        img: np.ndarray 或 PIL.Image
        detect_result: list/dict，格式为AprilTag检测返回的结果
        返回PIL.Image或None
        """
        # 如果检测结果为None，则返回None
        if detect_result is None:
            return None
            
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        # 转为np
        if isinstance(img, Image.Image):
            img_np = np.array(img)
        else:
            img_np = img
        overlay = img_np.copy()
        # 只绘制tag的多边形框和序号
        if detect_result and isinstance(detect_result, (list, tuple)):
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
        # 转为PIL
        overlay_pil = Image.fromarray(overlay.astype('uint8'), 'RGB')
        return overlay_pil

    def get_result_text(self, detect_result):
        """
        获取检测结果的文本描述。
        detect_result: list/dict，格式为AprilTag检测返回的结果
        返回: str，包含所有检测到的tag信息
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
                result_text.append(f"ID: {tag_id}, Center: {center}")
            else:
                result_text.append(str(r))
        return "\n".join(result_text)

    def _format_result(self, r):
        # pupil_apriltags的Detection对象转dict
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
    @staticmethod
    def from_config(config: dict):
        """从参数dict快速创建Tag36h11Detector实例（families强制为tag36h11）"""
        return Tag36h11Detector(
            nthreads=config.get('nthreads', 1),
            quad_decimate=config.get('quad_decimate', 1.0),
            quad_sigma=config.get('quad_sigma', 0.0),
            refine_edges=config.get('refine_edges', 1),
            decode_sharpening=config.get('decode_sharpening', 0.25),
            debug=config.get('debug', 0)
        )

    def __init__(self, **kwargs):
        super().__init__(families='tag36h11', **kwargs)


# 确保配置目录存在
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '../.config')
os.makedirs(CONFIG_DIR, exist_ok=True)

APRILTAG_CONFIG_PATH = os.path.join(CONFIG_DIR, 'apriltag_config.json')


def save_apriltag_config(path=APRILTAG_CONFIG_PATH):
    """保存config到json文件"""
    # 只保存tag36h11_config，结构为{'tag36h11': ...}，兼容后续手动添加其他family
    data = {'tag36h11': tag36h11_config.copy()}
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


def load_apriltag_config(path=APRILTAG_CONFIG_PATH):
    """从json文件读取配置并更新tag36h11config"""
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and 'tag36h11' in data:
            tag36h11_config.clear()
            tag36h11_config.update(data['tag36h11'])
            logger.info(f"已加载AprilTag配置: {tag36h11_config}", notify_gui=False)


def apply_apriltag_config():
    """应用当前配置到AprilTag检测器（重建全局检测器列表）"""
    global tag36h11_detectors
    tag36h11_detectors = [Tag36h11Detector.from_config(
        tag36h11_config) for _ in range(len(tag36h11_detectors))]
    logger.info(f"已应用AprilTag配置: {tag36h11_config}")


load_apriltag_config()  # 初始化时加载配置

tag36h11_detectors: list[Tag36h11Detector] = [
    Tag36h11Detector.from_config(tag36h11_config) for _ in range(3)
]
