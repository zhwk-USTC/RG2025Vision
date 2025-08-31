import asyncio
import time
import concurrent.futures as futures
from typing import Optional
import numpy as np
import threading

from core.logger import logger
from ..camera import Camera, CameraIntrinsics, CameraPose, CameraConfig
from ..types import CamNodeConfig, TagDetections, TagDetectionConfig

from ..detection.apriltag import Tag36h11Detector


class CameraNode:
    """
    单相机“外部包装”节点（无后台循环）：
      - start()/stop() 仅负责连接/断开相机
      - 只有在调用 detect_once() 时才：
            取一帧 -> 在后台线程跑一次检测 -> 返回结果
      - 支持 asyncio 并发：对多个 CameraNode 同时 await detect_once()

    设计要点：
      - 每个节点内置一个 ThreadPoolExecutor(max_workers=1)，
        同一相机不会并行跑多个检测（按调用顺序排队执行）；
        多个相机之间则可并行。
    """

    def __init__(
        self,
        config: Optional[CamNodeConfig] = None,
    ) -> None:
        self.alias: str = config.alias if config else "未选择摄像头"
        self._camera: Optional[Camera] = None
        if config and config.camera:
            self._camera = Camera()
            self._camera.select_by_index(config.camera.index)
        self._latest_frame: Optional[np.ndarray] = None
        self.detection_fps: float = 0.0

        self.camera_intrinsics: Optional[CameraIntrinsics] = None
        self.camera_pose: Optional[CameraPose] = None

        self._tag36h11_detector: Optional[Tag36h11Detector] = Tag36h11Detector(
            config.tag36h11) if config and config.tag36h11 else None
        self._latest_tag36h11_detection: Optional[TagDetections] = None
        self._latest_tag36h11_detection
        self._executor = futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=f"det-{config.alias if config else 'cam'}")

        self._lock = threading.Lock()

    # ---------- 生命周期 ----------
    @property
    def is_open(self) -> bool:
        if not self._camera:
            return False
        return self._camera.is_open

    def start(self) -> bool:
        """连接相机"""
        if self.is_open:
            return True
        if not self._camera:
            return False
        ok = self._camera.connect()
        return ok

    def stop(self) -> None:
        """断开相机并清理"""
        try:
            if self.is_open and self._camera:
                self._camera.disconnect()
        finally:
            # 不立刻 shutdown，允许未完成的 detect_once() 收尾
            pass

    def close(self) -> None:
        """彻底关闭（含线程池）"""
        self.stop()
        self._executor.shutdown(cancel_futures=True)

    def select_camera_by_index(self, camera_index: int) -> None:
        if self._camera is None:
            self._camera = Camera()
        self._camera.select_by_index(camera_index)
        logger.info(f"CameraNode[{self.alias}] 选择相机 {self.camera_name}")

    # ---------- 一次性异步检测（核心） ----------

    async def read_frame(self) -> Optional[np.ndarray]:
        if not self._camera:
            raise RuntimeError(f"CameraNode[{self.alias}] 相机未初始化")
        if not self.is_open:
            raise RuntimeError(f"CameraNode[{self.alias}] 相机未连接")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._camera.read_frame)

    async def read_frame_and_detect(self) -> Optional[TagDetections]:
        """
        触发一次检测（异步，不阻塞事件循环）。
        - 同一相机的多次调用会排队（单线程池），多个相机可并发。
        - 若相机未连接且 autoconnect=True，会自动连接；否则抛错。
        - 返回 None 表示：未取到帧或检测器返回异常被捕获。
        """
        if self._camera is None:
            raise RuntimeError(f"CameraNode[{self.alias}] 相机未初始化")
        if not self.is_open:
            raise RuntimeError(f"CameraNode[{self.alias}] 相机未连接")

        # 拍一帧或取最新帧
        frame = await self.read_frame()
        self._latest_frame = frame

        self._update_fps()

        if frame is None or self._tag36h11_detector is None:
            self._latest_tag36h11_detection = None
            return None

        loop = asyncio.get_running_loop()

        # 在线程池中执行检测逻辑，避免阻塞主线程
        result = await loop.run_in_executor(
            self._executor,
            self._tag36h11_detector.detect,
            frame, self.camera_intrinsics, 1.0
        )
        self._latest_tag36h11_detection = result
        return result
        

    def _update_fps(self) -> None:
        """更新 FPS"""
        _fps_alpha: float = 0.2
        # 计时（用单调钟，计算真实帧间隔）
        t_now = time.perf_counter()
        ts_wall = time.time()
        if hasattr(self, '_t_prev') and self._t_prev is not None:
            dt = t_now - self._t_prev
            if dt > 0:
                inst_fps = 1.0 / dt
                self.detection_fps = inst_fps if self.detection_fps is None else (
                    _fps_alpha * inst_fps +
                    (1.0 - _fps_alpha) * self.detection_fps
                )
        self._t_prev = t_now
        self.latest_frame_time = ts_wall

    # ---------- 快照读取 ----------
    @property
    def latest_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._latest_frame

    @property
    def latest_tag36h11_detection(self) -> Optional[TagDetections]:
        with self._lock:
            return self._latest_tag36h11_detection
        
    @property
    def status(self) -> str:
        lines = []
        # 相机别名
        lines.append(f"别名: {self.alias}")
        
        # 相机状态（连接状态）
        camera_status = "已连接" if self.is_open else "未连接"
        lines.append(f"状态: {camera_status}")
        
        lines.append(f"相机配置: \n {str(self._camera) if self._camera else '未初始化'}")
        
        # FPS
        lines.append(f"实时FPS: {self.detection_fps:.2f}")
        
        # 最新检测结果状态
        if self._tag36h11_detector:
            lines.append(f"Tag36h11 检测器: 已启用")
        else:
            lines.append(f"Tag36h11 检测器: 未启用")
        if self._latest_tag36h11_detection:
            lines.append(f"{len(self._latest_tag36h11_detection)} 个标签检测到")
        else:
            lines.append(f"无检测数据")
        
        # 返回状态信息
        return "\n".join(lines)
    
    @property
    def camera_index(self) -> Optional[int]:
        return self._camera.info.index if self._camera and self._camera.info else None
        
    @property
    def camera_name(self) -> Optional[str]:
        return self._camera.info.name if self._camera and self._camera.info else None
    
    @property
    def width(self) -> Optional[int]:
        return self._camera.width if self._camera and self._camera.info else None
        
    @property
    def height(self) -> Optional[int]:
        return self._camera.height if self._camera and self._camera.info else None

    @property
    def camera_fps(self) -> Optional[float]:
        return self._camera.fps if self._camera and self._camera.info else None

    def set_width(self, width: int):
        if self._camera:
            self._camera.width = width
            logger.info(f"摄像头 {self.camera_name} 的宽度已更改为 {width}")
        else:
            logger.warning(f"摄像头 {self.camera_name} 未初始化，无法更改宽度")

    def set_height(self, height: int):
        if self._camera:
            self._camera.height = height
            logger.info(f"摄像头 {self.camera_name} 的高度已更改为 {height}")
        else:
            logger.warning(f"摄像头 {self.camera_name} 未初始化，无法更改高度")

    def set_camera_fps(self, fps: int):
        if self._camera:
            self._camera.fps = fps
            logger.info(f"摄像头 {self.camera_name} 的帧率已更改为 {fps}")
        else:
            logger.warning(f"摄像头 {self.camera_name} 未初始化，无法更改帧率")

    def get_config(self) -> CamNodeConfig:
        if self._camera:
            return CamNodeConfig(
                alias=self.alias,
                camera=self._camera.get_config(),
                intrinsics=self.camera_intrinsics,
                pose=self.camera_pose if self._camera else None,
                tag36h11=self._tag36h11_detector.get_config() if self._tag36h11_detector else None
            )
        else:
            return CamNodeConfig()
        
    def set_config(self, config: CamNodeConfig) -> None:
        self._camera = Camera(config.camera)
        self.alias = config.alias
        self.camera_intrinsics = config.intrinsics
        self.camera_pose = config.pose
        self._tag36h11_detector = Tag36h11Detector(config.tag36h11) if config.tag36h11 else None