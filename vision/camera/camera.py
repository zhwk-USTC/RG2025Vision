import cv2
import numpy as np
import time
import platform
from typing import Optional, Any

from ..types import CameraConfig
from .manager import CameraInfo, get_camera_info_list
from core.logger import logger


class Camera:
    """
    设备层相机：负责连接、采帧与基本参数维护。
    """

    def __init__(self, config: Optional[CameraConfig] = None) -> None:
        # 基本信息
        self.info: Optional[CameraInfo] = None
        self.connected: bool = False
        self.cap: Optional[cv2.VideoCapture] = None

        # 请求的视频参数（连接前可设置）
        self.width: Optional[int] = None       # 实际值在 connect 后回读覆盖
        self.height: Optional[int] = None
        self.fps: Optional[float] = None       # 实际值在 connect 后回读覆盖
        
        if config:
            try:
                self.select_by_index(config.index)
            except Exception as e:
                logger.error(f"摄像头初始化失败: {e}")
                self.info = None
                return
            self.width = config.width
            self.height = config.height
            self.fps = config.fps

    # -------------------------- 连接/断开 --------------------------

    def select_by_info(self, info: CameraInfo) -> None:
        """通过 CameraInfo 选择摄像头"""
        self.info = info
        self.cap = None
        logger.info(f"{self.info.name} 已选择: {self.info.name} (index={self.info.index})")

    def select_by_index(self, camera_index: int) -> None:
        """通过索引选择摄像头"""
        cam_info_list = get_camera_info_list()
        if camera_index < 0 or camera_index >= len(cam_info_list):
            raise IndexError(f"无效的摄像头索引: {camera_index}")
        self.select_by_info(cam_info_list[camera_index])

    @property
    def is_open(self) -> bool:
        return bool(self.connected and self.cap is not None and self.cap.isOpened())

    def connect(self) -> bool:
        """连接设备并应用参数设置；回读实际参数"""
        if self.info is None:
            raise ValueError(
                "请先选择摄像头（select_camera_by_index / select_camera_info）")
        if self.connected:
            self.disconnect()

        try:
            backend = getattr(self.info, "backend", 0)
            self.cap = cv2.VideoCapture(self.info.index, backend)
            time.sleep(0.25)  # 设备初始化等待（少量即可）

            if not self.cap.isOpened():
                raise ConnectionError(f"无法打开摄像头 {self.info.name}")

            # Linux: MJPEG 以提升带宽利用率（若不支持，set 返回 False）
            if platform.system() == "Linux":
                ok_fourcc = self.cap.set(
                    cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # type: ignore
                if not ok_fourcc:
                    logger.debug("设置 MJPG FourCC 失败，后端可能不支持")

            # 应用请求参数（若已设置）
            if self.width and self.height:
                ok_w = self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                ok_h = self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                if not (ok_w and ok_h):
                    logger.debug("设置分辨率失败（后端可能不支持），将回读实际分辨率")

            if self.fps:
                ok_fps = self.cap.set(cv2.CAP_PROP_FPS, float(self.fps))
                if not ok_fps:
                    logger.debug("设置 FPS 失败（后端可能不支持），将回读实际 FPS")

            # 尝试缩小缓冲，降低延迟（并非所有后端支持）
            try:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            # 回读实际参数
            real_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                         ) or self.width or 0
            real_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                         ) or self.height or 0
            real_fps = float(self.cap.get(cv2.CAP_PROP_FPS)
                             ) or (self.fps or 0.0)

            self.width, self.height, self.fps = real_w, real_h, real_fps

            # 读一帧做热身
            ret, frame = self.cap.read()
            if not ret:
                raise RuntimeError(f"摄像头 {self.info.name} 初始帧读取失败")

            # 设置状态
            self.connected = True
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            logger.info(
                f"已连接 {self.info.name} ({self.width}x{self.height} @ {self.fps:.1f}fps)")
            return True

        except Exception as e:
            logger.error(f"摄像头 {self.info.name} 连接失败: {e}")
            # 确保资源被释放与状态复位
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """断开设备连接并清空运行时状态"""
        # 释放摄像头资源（若存在）
        try:
            if self.cap is not None:
                self.cap.release()
        finally:
            self.cap = None

        # 复位状态（无论是否选择过设备）
        self.connected = False

        if self.info:
            logger.info(f"已断开 {self.info.name}")
        else:
            logger.info("已断开摄像头")

    # -------------------------- 采帧 --------------------------

    def read_frame(self) -> "cv2.typing.MatLike":
        """读取一帧图像，更新实际帧率（EMA），返回 RGB"""
        if not self.is_open:
            raise RuntimeError("摄像头未连接")

        # 读取
        ret, frame = self.cap.read()  # type: ignore[union-attr]
        if not ret:
            raise RuntimeError("读取摄像头帧失败")

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        return frame
    
    def get_config(self) -> CameraConfig:
        if not self.info:
            return CameraConfig()
        return CameraConfig(
            index=self.info.index,
            width=self.width if self.width else 1080,
            height=self.height if self.height else 720,
            fps=self.fps if self.fps else 30
        )

    def __str__(self) -> str:
        return ('Camera: '+
                '\nname: '+ str(self.info.name if self.info else "未知") +
                '\nindex: '+ str(self.info.index if self.info else -1) +
                '\nconnected: '+ str(self.connected) +
                '\nwidth: '+ str(self.width) +
                '\nheight: '+ str(self.height) +
                '\nfps: '+ str(self.fps)
        )
