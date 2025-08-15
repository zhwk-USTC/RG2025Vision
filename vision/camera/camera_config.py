"""
摄像头配置模块

负责摄像头配置的保存和加载，独立于摄像头操作逻辑。
"""

import json
import os
import inspect
from typing import List, Optional, Dict, Any
from core.logger import logger
from .camera import Camera, camera_info_list
from .intrinsics import CameraIntrinsics

# 确保配置目录存在
CONFIG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../.config'))
os.makedirs(CONFIG_DIR, exist_ok=True)

# 默认配置文件路径
CAMERA_CONFIG_PATH = os.path.join(CONFIG_DIR, 'camera_config.json')
CAMERA_INTRINSICS_PATH = os.path.join(CONFIG_DIR, 'camera_intrinsics.json')


def save_config(cameras_list: List[Camera], config_path: str = CAMERA_CONFIG_PATH) -> bool:
    """保存摄像头配置
    
    Args:
        cameras_list: 要保存配置的摄像头列表
        config_path: 配置文件路径，默认使用全局配置路径
        
    Returns:
        bool: 是否保存成功
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
        
        config = []
        for cam in cameras_list:
            config.append({
                'alias': cam.alias,
                'path': cam.info.path if cam.info else None,
                'width': cam.width,
                'height': cam.height,
                'fps': cam.fps,
                'tag36h11_enabled': cam.tag36h11_enabled
            })
            
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
        abs_path = os.path.abspath(config_path)
        logger.info(f"摄像头配置已保存到 {abs_path}")
        return True
    except Exception as e:
        logger.error(f"保存摄像头配置失败: {e}")
        return False

def load_config(cameras_list: List[Camera], config_path: str = CAMERA_CONFIG_PATH) -> bool:
    """加载摄像头配置
    
    Args:
        cameras_list: 要加载配置的摄像头列表
        config_path: 配置文件路径，默认使用全局配置路径
        
    Returns:
        bool: 是否成功加载配置
    """
    if not os.path.exists(config_path):
        logger.warning(f"摄像头配置文件不存在: {config_path}")
        return False
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        for i, cam_cfg in enumerate(config):
            if i >= len(cameras_list):
                break
                
            cam = cameras_list[i]
            
            # 先根据 path 匹配摄像头
            path = cam_cfg.get('path')
            if path:
                for info in camera_info_list:
                    if hasattr(info, 'path') and info.path == path:
                        cam.info = info
                        break
                        
            cam.alias = cam_cfg.get('alias')
            cam.width = cam_cfg.get('width')
            cam.height = cam_cfg.get('height')
            cam.fps = cam_cfg.get('fps')
            cam.tag36h11_enabled = cam_cfg.get('tag36h11_enabled', True)
            
            logger.info(
                f"摄像头 {i} 配置已加载: {cam.alias} ({cam.info.name if cam.info else '未知'}) ({cam.width}x{cam.height} @ {cam.fps}fps)"
            )
        return True
    except Exception as e:
        logger.error(f"加载摄像头配置失败: {e}")
        return False


def load_intrinsics(cameras_list: List[Camera], intrinsics_path: str = CAMERA_INTRINSICS_PATH):
    """从文件加载相机内参
    
    Args:
        file_path: 内参文件路径
        
    Returns:
        CameraIntrinsics: 加载的内参对象，失败则返回None
    """
    if not os.path.exists(intrinsics_path):
        logger.warning(f"内参文件不存在: {intrinsics_path}")
        return None
    
    try:
        with open(intrinsics_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for i, cam_cfg in enumerate(data):
            if i >= len(cameras_list):
                break
            # 获取类的字段名列表
            params = inspect.signature(CameraIntrinsics).parameters
            valid_fields = list(params.keys())
            
            # 过滤出有效的字段
            filtered_data = {k: v for k, v in cam_cfg.items() if k in valid_fields}

            # 确保必需字段都存在
            required_fields = [name for name, param in params.items() 
                            if param.default == inspect.Parameter.empty]
            missing = [field for field in required_fields if field not in filtered_data]
            
            if missing:
                logger.warning(f"相机内参文件缺少必需字段: {missing}")
                intrinsics = None
            else:
                intrinsics = CameraIntrinsics(**filtered_data)
            cameras_list[i].intrinsics = intrinsics
            logger.info(f"摄像头 {i} 内参已加载: {intrinsics}")
    except Exception as e:
        logger.error(f"加载相机内参失败: {e}")
        return None
