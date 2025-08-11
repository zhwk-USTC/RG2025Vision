import cv2
import time
import platform
from typing import Optional
from cv2_enumerate_cameras import enumerate_cameras

from .intrinsics import CameraIntrinsics
from core.logger import logger

camera_info_list = []


def setup_camera_info():
    """初始化摄像头信息"""
    global camera_info_list
    # 根据操作系统选择合适的摄像头后端
    if platform.system() == "Windows":
        backend = cv2.CAP_MSMF
    elif platform.system() == "Linux":
        backend = cv2.CAP_V4L2
    else:  # macOS
        backend = cv2.CAP_AVFOUNDATION
    
    camera_info_list = enumerate_cameras(backend)

    for info in camera_info_list:
        info.name = info.name + f" ({info.index})"

    logger.info(f"已找到 {len(camera_info_list)} 个摄像头")
    for idx, info in enumerate(camera_info_list):
        name = getattr(info, 'name', None)
        logger.info(f"  [{idx}] {name if name else info}")


setup_camera_info()


class Camera:
    def __init__(self):
        # 基本信息
        self.alias = None
        self.info = None
        self.connected = False
        self.cap = None

        # 视频参数
        self.width = None
        self.height = None
        self.fps = None
        self.actual_fps = None  # 实际帧率（EMA平滑）
        self._fps_alpha = 0.2  # EMA平滑系数，越大越灵敏，越小越平滑

        self.latest_frame = None
        self.last_frame_time = None  # 上一帧时间戳
        self.actual_fps = None  # 实际帧率

        self.tag36h11_enabled = True  # 是否启用 tag36h11 检测
        
        # 摄像头内参
        self.intrinsics: Optional[CameraIntrinsics] = None  # CameraIntrinsics对象

        self.extra_data = {}

    def select_camera(self, camera_index: int):
        """选择摄像头"""
        if self.connected:
            self.disconnect()
        if camera_index < 0 or camera_index >= len(camera_info_list):
            logger.error(f"无效的摄像头索引: {camera_index}")
            return

        self.info = camera_info_list[camera_index]
        self.connected = False
        self.cap = None
        self.latest_frame = None

        logger.info(
            f"{self.alias} 已选择摄像头: {self.info.name} ({self.info.index})"
        )

    def connect(self) -> bool:
        """连接设备并应用参数设置

        Returns:
            bool: 连接成功返回True
        """
        if self.info is None:
            raise ValueError("请先选择摄像头")
        if self.connected:
            self.disconnect()

        try:
            self.cap = cv2.VideoCapture(self.info.index, self.info.backend)
            time.sleep(0.3)  # 设备初始化等待

            if not self.cap.isOpened():
                raise ConnectionError(f"无法打开摄像头 {self.info.name}")

            # Linux优化：设置视频格式为MJPEG以提高性能
            if platform.system() == "Linux":
                # 尝试设置MJPEG格式以减少带宽需求
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')) #type: ignore
            
            # 应用分辨率设置
            if self.width and self.height:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            # 应用帧率设置
            if self.fps:
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 验证设备参数
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)

            # 首次帧测试
            ret, frame = self.cap.read()
            if not ret:
                self.disconnect()
                logger.error(f"摄像头 {self.info.name} 初始帧读取失败")
                return False

            self.connected = True
            logger.info(
                f"已连接 {self.info.name} ({self.width}x{self.height} @ {self.fps:.1f}fps)"
            )
            return True

        except Exception as e:
            self.disconnect()
            logger.error(f"摄像头 {self.info.name} 连接失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开设备连接"""
        if self.cap is None or self.info is None:
            logger.warning("未选择摄像头")
            return
        if not self.connected:
            logger.info(f"摄像头 {self.info.name} 未连接，无需断开")
        # 释放摄像头资源
        if self.cap:
            self.cap.release()
            self.cap = None

        self.connected = False
        self.latest_frame = None
        self.last_frame_time = None
        self.actual_fps = None
        self.extra_data.clear()
        logger.info(f"已断开 {self.info.name}")

    def read_frame(self) -> cv2.typing.MatLike:
        """读取一帧图像，并计算实际帧率 actual_fps

        Returns:
            cv2.typing.MatLike: 返回图像帧
        """
        if not self.connected or self.cap is None:
            raise RuntimeError("摄像头未连接")

        now = time.time()
        if self.last_frame_time is not None:
            interval = now - self.last_frame_time
            if interval > 0:
                inst_fps = 1.0 / interval
                if self.actual_fps is None:
                    self.actual_fps = inst_fps
                else:
                    self.actual_fps = self._fps_alpha * inst_fps + \
                        (1 - self._fps_alpha) * self.actual_fps
        self.last_frame_time = now

        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("读取摄像头帧失败")

        # OpenCV 默认是BGR，转为RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.latest_frame = rgb_frame.copy()
        return rgb_frame

# CameraIntrinsics 已移至 intrinsics.py
# 摄像头配置的保存和加载功能已移至 camera_config.py