"""
摄像头配置模块：负责摄像头配置、内参与外参的保存/加载（独立于采集与运行时逻辑）
"""

import json
import os
import inspect
from typing import List, Dict

from core.logger import logger
from .camera import Camera, CameraIntrinsics, camera_info_list, CameraPose
from .tag_loc import TagPose

# 配置目录与文件路径
CONFIG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "../.config"))
os.makedirs(CONFIG_DIR, exist_ok=True)

CAMERA_CONFIG_PATH = os.path.join(CONFIG_DIR, "camera_config.json")
CAMERA_INTRINSICS_PATH = os.path.join(CONFIG_DIR, "camera_intrinsics.json")
CAMERA_POSE_PATH = os.path.join(CONFIG_DIR, "camera_pose.json")
APRILTAG_POSE_PATH = os.path.join(CONFIG_DIR, "apriltag_pose.json")


def save_camera_config(cameras: List[Camera]) -> bool:
    """保存摄像头基础配置（别名、路径、分辨率、帧率、tag 开关）"""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(CAMERA_CONFIG_PATH)), exist_ok=True)
        config = [
            {
                "alias": cam.alias,
                "path": getattr(cam.info, "path", None) if cam.info else None,
                "width": cam.width,
                "height": cam.height,
                "fps": cam.fps,
                "tag36h11_enabled": cam.tag36h11_enabled,
            }
            for cam in cameras
        ]
        with open(CAMERA_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"摄像头配置已保存到 {os.path.abspath(CAMERA_CONFIG_PATH)}")
        return True
    except Exception as e:
        logger.error(f"保存摄像头配置失败: {e}")
        return False


def load_camera_config(cameras: List[Camera]) -> bool:
    """加载摄像头基础配置到给定的 cameras 列表（按索引对应）"""
    if not os.path.exists(CAMERA_CONFIG_PATH):
        logger.warning(f"摄像头配置文件不存在: {CAMERA_CONFIG_PATH}")
        return False

    try:
        with open(CAMERA_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        for i, cam_cfg in enumerate(config):
            if i >= len(cameras):
                break

            cam = cameras[i]

            # 根据 path 绑定 CameraInfo
            path = cam_cfg.get("path")
            if path:
                for info in camera_info_list:
                    if getattr(info, "path", None) == path:
                        cam.info = info
                        break

            cam.alias = cam_cfg.get("alias")
            cam.width = cam_cfg.get("width")
            cam.height = cam_cfg.get("height")
            cam.fps = cam_cfg.get("fps")
            cam.tag36h11_enabled = cam_cfg.get("tag36h11_enabled", True)

            logger.info(
                f"摄像头 {i} 配置已加载: {cam.alias} "
                f"({getattr(cam.info, 'name', '未知')}) "
                f"({cam.width}x{cam.height} @ {cam.fps}fps)"
            )
        return True
    except Exception as e:
        logger.error(f"加载摄像头配置失败: {e}")
        return False


def load_camera_intrinsics(cameras: List[Camera]) -> bool:
    """从文件加载相机内参到 cameras[i].intrinsics（按索引对应）"""
    if not os.path.exists(CAMERA_INTRINSICS_PATH):
        logger.warning(f"内参文件不存在: {CAMERA_INTRINSICS_PATH}")
        return False

    try:
        with open(CAMERA_INTRINSICS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        params = inspect.signature(CameraIntrinsics).parameters
        valid_fields = list(params.keys())
        required_fields = [name for name, p in params.items() if p.default is inspect._empty]

        loaded = 0
        for i, cam_cfg in enumerate(data):
            if i >= len(cameras):
                break

            filtered = {k: v for k, v in cam_cfg.items() if k in valid_fields}
            missing = [k for k in required_fields if k not in filtered]
            if missing:
                logger.warning(f"相机 {i} 内参缺少字段: {missing}")
                cameras[i].intrinsics = None
                continue

            try:
                intr = CameraIntrinsics(**filtered)
            except Exception as e:
                logger.warning(f"相机 {i} 内参解析失败: {e}")
                cameras[i].intrinsics = None
                continue

            cameras[i].intrinsics = intr
            loaded += 1
            logger.info(f"摄像头 {i} 内参已加载: {intr}")

        if loaded == 0:
            logger.warning("未能为任何相机加载内参")
            return False
        return True

    except Exception as e:
        logger.error(f"加载相机内参失败: {e}")
        return False


def load_camera_pose(cameras: List[Camera]) -> bool:
    """
    从文件加载摄像头二维外参到 cameras[i].pose（JSON 为 list[{'x','y','yaw'}]，按索引对应）
    """
    if not os.path.exists(CAMERA_POSE_PATH):
        logger.warning(f"摄像头位姿文件不存在: {CAMERA_POSE_PATH}")
        return False

    try:
        with open(CAMERA_POSE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"读取摄像头位姿文件失败: {e}")
        return False

    if not isinstance(data, list):
        logger.error("位姿文件格式错误，应为 list[dict]")
        return False

    loaded = 0
    for i, cam in enumerate(cameras):
        if i >= len(data):
            break
        try:
            cfg = data[i]
            cam.pose = CameraPose(
                x=float(cfg["x"]),
                y=float(cfg["y"]),
                yaw=float(cfg["yaw"]),
            )
            loaded += 1
            logger.info(f"摄像头 {i} 位姿已加载: {cam.pose}")
        except Exception as e:
            logger.warning(f"相机 {i} 位姿解析失败: {e}")

    if loaded == 0:
        logger.warning("未能为任何相机加载位姿")
        return False
    return True


def load_apriltag_pose(apriltag_map: Dict[int, TagPose]):
    """预留：加载 AprilTag 位姿到字典 apriltag_map（未实现）"""
    pass
