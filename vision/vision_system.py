import asyncio
import time
import numpy as np
from typing import Dict, Iterable, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import threading

from core.logger import logger
from .camera import Camera, scan_cameras, CameraConfig
from .detection.apriltag import TagDetections, TagDetectionConfig, Tag36h11Detector, AprilTagDetectorBase
from .detection.types import CameraIntrinsics
from .localization.localizer import Localizer, LocalizerConfig
from concurrent.futures import ThreadPoolExecutor, as_completed
# from .camera_node import CamNodeConfig


@dataclass(slots=True)
class FramePacket:
    img_bgr: np.ndarray
    t_ns: int
    idx: int


@dataclass(slots=True)
class TagDetectionPacket:
    img_bgr: np.ndarray
    t_ns: int
    idx: int
    dets: TagDetections


@dataclass
class VisionSystemConfig:
    # key: cam key, value: cam config dict
    cameras: Dict[str, CameraConfig] = field(default_factory=dict)
    camera_metadata: Dict[str, dict] = field(default_factory=dict)  # 存储相机内参等元信息
    tag36h11_detectors: Dict[str, TagDetectionConfig] = field(default_factory=dict)
    tag36h11_size: Optional[float] = None  # 标签边长，单位米
    # localizer: Optional[LocalizerConfig] = None


class VisionSystem:
    """
    多相机系统管理：
      - 统一启动/停止多个 CameraNode
      - 并发触发“一次性检测”（detect_once_all）
      - 读取所有/指定相机的最近检测（latest_tags_all）
      - 健康状态汇总（node_stats）

    设计要点：
      - 不跑后台循环；只有在你调用 detect_once_* 时才触发每个相机一次检测
      - 内部使用 asyncio.gather 同步等待多个相机并发完成
      - 同一相机内部不并行（由 CameraNode 的单线程池保证）
    """

    def __init__(
        self,
        VisionSystemConfig: Optional[VisionSystemConfig] = None,
    ) -> None:
        self._cameras: Dict[str, Camera] = {}
        self._camera_metadata: Dict[str, dict] = {}
        self._latest_frame_packets: Dict[str, Optional[FramePacket]] = {}
        self._frame_lock = threading.Lock()
        
        self._latest_detection_packets: Dict[str,
                                             Optional[TagDetectionPacket]] = {}
        self._detection_lock = threading.Lock()
        self._apriltag_36h11_detectors: Dict[str, Tag36h11Detector] = {}
        self._tag36h11_size: Optional[float] = None  # 标签边长，单位米

        self.localizer: Optional[Localizer] = None

        scan_cameras()
        try:
            if VisionSystemConfig is not None:
                cam_configs = VisionSystemConfig.cameras
                for key, cam_config in cam_configs.items():
                    cam = Camera(cam_config)
                    self._cameras[key] = cam
                    logger.info(f"[VisionSystem] 添加相机 {key}: {cam.name}")
                tag36h11_detector_configs = VisionSystemConfig.tag36h11_detectors
                # 创建 36h11 检测器（若配置了）
                for key, det_config in tag36h11_detector_configs.items():
                    detector = Tag36h11Detector(det_config)
                    self._apriltag_36h11_detectors[key] = detector
                    logger.info(f"[VisionSystem] 添加 36h11 检测器 {key}")
                
                self._tag36h11_size = VisionSystemConfig.tag36h11_size
                self._camera_metadata = VisionSystemConfig.camera_metadata

        except Exception as e:
            logger.error(f"[VisionSystem] 初始化异常: {e}")
        else:
            logger.info(f"[VisionSystem] 初始化完成")

    # ---------------- 基本操作 ----------------
    def add_camera(self, key: str, cam: Camera = Camera()) -> None:
        self._cameras[key] = cam
        logger.info(f"[VisionSystem] 添加相机 {key}: {cam.name}")
        
    def remove_camera(self, key: str) -> None:
        if key in self._cameras:
            del self._cameras[key]
        if key in self._latest_frame_packets:
            del self._latest_frame_packets[key]
        logger.info(f"[VisionSystem] 移除相机 {key}")
        self.remove_tag36h11_detector(key)

    def add_tag36h11_detector(self, key: str, detector: Tag36h11Detector = Tag36h11Detector()) -> None:
        if key not in self._cameras:
            logger.warning(f"[VisionSystem] 添加 tag36h11 检测器失败: 未找到相机 {key}")
            return
        self._apriltag_36h11_detectors[key] = detector
        logger.info(f"[VisionSystem] 添加 tag36h11 检测器 {key}")
        
    def remove_tag36h11_detector(self, key: str) -> None:
        if key in self._apriltag_36h11_detectors:
            del self._apriltag_36h11_detectors[key]
        if key in self._latest_detection_packets:
            del self._latest_detection_packets[key]
        logger.info(f"[VisionSystem] 移除 tag36h11 检测器 {key}")

    def start(self) -> bool:
        """
        连接所有相机
        返回是否全部成功。
        """
        ok_all = True
        for key, cam in self._cameras.items():
            try:
                ok = cam.connect()
                ok_all = ok_all and ok
            except Exception as e:
                logger.warning(f"[VisionSystem] 启动相机失败 {key}: {e}")
                ok_all = False
        return ok_all

    def stop(self) -> None:
        """
        断开所有相机
        """
        for key, cam in self._cameras.items():
            try:
                cam.disconnect()
            except Exception as e:
                logger.warning(f"[VisionSystem] 停止相机失败 {key}: {e}")

    def close(self) -> None:
        """彻底关闭"""
        self.stop()

    # ---------------- 同步更新 ----------------
    def _update_frames(self, keys: Optional[Union[str,List[str]]] = None) -> None:
        """
        并发调用所有相机进行一次采帧（不触发检测），
        并把最新帧写入 self._latest_frames[cam_key]。
        """
        
        # 选择要抓取的相机
        if keys is None:
            targets = list(self._cameras.items())
        elif isinstance(keys, str):
            if keys not in self._cameras:
                logger.warning(f"[VisionSystem] update_frames 未找到相机 {keys}")
                return
            targets = [(keys, self._cameras[keys])]
        else:  # list[str]
            targets = []
            for k in keys:
                if k in self._cameras:
                    targets.append((k, self._cameras[k]))
                else:
                    logger.warning(f"[VisionSystem] update_frames 未找到相机 {k}")

        cams = list(self._cameras.items())
        if not cams:
            return

        max_workers = max(1, len(targets))

        def _safe_read(pair):
            key, cam = pair
            try:
                # 优先用 read_frame_packet()（含时间戳/帧号）
                if hasattr(cam, "read_frame_packet"):
                    frame, t_ns, idx = cam.read_frame_packet()  # BGR
                else:
                    # 兜底：用 read_frame() + 即时时间戳；idx 用 -1 表示未知
                    frame = cam.read_frame()
                    t_ns, idx = time.perf_counter_ns(), -1

                payload = FramePacket(
                    img_bgr=frame,
                    t_ns=t_ns,
                    idx=idx,
                )

                return key, payload, None
            except Exception as e:
                return key, None, e

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(_safe_read, pair) for pair in targets]
            for fut in as_completed(futures):
                k, payload, err = fut.result()
                if err is not None:
                    logger.warning(
                        f"[VisionSystem] read_frame {k} 异常: {err}")
                    continue
                # 写入最新帧缓存（线程安全）
                with self._frame_lock:
                    self._latest_frame_packets[k] = payload


    def _detect_tag36h11(self, keys: Optional[Union[str, List[str]]] = None) -> None:
        """
        使用最新帧缓存做一次 tag36h11 检测（并发）。
        keys: None=全量；str=单路；List[str]=多路
        """
        # 归一化目标键
        if keys is None:
            target_keys = list(self._cameras.keys())
        elif isinstance(keys, str):
            target_keys = [keys] if keys in self._cameras else []
        else:
            target_keys = [k for k in keys if k in self._cameras]

        if not target_keys:
            return

        # 复制帧快照（缩短持锁时间）
        with self._frame_lock:
            latest_snap: Dict[str, Optional[FramePacket]] = {
                k: self._latest_frame_packets.get(k) for k in target_keys
            }

        # 结果容器与待工作键（在检测锁内仅做轻量检查，不做重活）
        results: Dict[str, Optional["TagDetectionPacket"]] = {}
        work_keys: List[str] = []
        with self._detection_lock:
            for k in target_keys:
                # 必须有对应检测器
                if k not in self._apriltag_36h11_detectors:
                    results[k] = None
                    continue

                pkt = latest_snap.get(k)
                if pkt is None:
                    results[k] = None
                    continue

                # 只判 None，避免 numpy 的布尔歧义
                img_bgr = getattr(pkt, "img_bgr", None)
                if img_bgr is None:
                    results[k] = None
                    continue

                # # （可选）要求内参存在；否则跳过
                # intr = self._camera_metadata.get(k, {}).get("intrinsics")
                # if intr is None:
                #     results[k] = None
                #     continue

                work_keys.append(k)

        if not work_keys:
            return

        # 并发检测（不持有 detection_lock）
        tag_size = self._tag36h11_size

        def _work(k: str):
            try:
                det = self._apriltag_36h11_detectors[k]
                pkt = latest_snap[k]
                # 这里 pkt 不会是 None，因为已在 work_keys 里筛过
                img: np.ndarray = pkt.img_bgr  # type: ignore[assignment]
                intr = self._camera_metadata.get(k, {}).get("intrinsics")
                dets = det.detect(image=img, intrinsics=intr, tag_size=tag_size)
                return k, pkt, dets
            except Exception as e:
                raise RuntimeError(f"相机 {k} 检测过程异常: {type(e).__name__}: {e}")

        with ThreadPoolExecutor(max_workers=len(work_keys)) as ex:
            futs = {ex.submit(_work, k): k for k in work_keys}
            for fut in as_completed(futs):
                k = futs[fut]
                try:
                    cam_key, pkt, dets = fut.result()
                    if pkt is None or dets is None:
                        results[cam_key] = None
                        continue
                    results[cam_key] = TagDetectionPacket(
                        img_bgr=pkt.img_bgr,
                        t_ns=pkt.t_ns,
                        idx=pkt.idx,
                        dets=dets,
                    )
                except Exception as e:
                    logger.warning(f"[VisionSystem] detect_tag36h11 {k} 异常: {e}")
                    results[k] = None

        with self._detection_lock:
            self._latest_detection_packets.update(results)

    def _detect(self) -> None:
        self._detect_tag36h11()

    def update(self) -> None:
        """
        同步（阻塞）调用所有相机进行一次联合定位检测
        """
        try:
            self._update_frames()  # 先采帧
            raise NotImplementedError
            # 创建检测任务列表
            tasks = [
                node.read_frame_and_detect_async()
                for node in self._cameras
            ]
            results = asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            out: List[Optional[TagDetections]] = []
            for node, res in zip(self._cameras, results):
                alias = node.alias
                if isinstance(res, BaseException):
                    logger.warning(
                        f"[VisionSystem] detect_once {alias} 异常: {res}")
                    res = None
                out.append(res)
        except Exception as e:
            logger.error(f"[VisionSystem] update 异常: {e}")

    # ---------------- 读取最近检测 ----------------

    def get_latest_frame_packet(self, cam_key: str) -> Optional[FramePacket]:
        """线程安全获取某路相机最新帧（可能 None）。返回 dict: {img_bgr, t_ns, idx, size}"""
        with self._frame_lock:
            if cam_key not in self._cameras:
                logger.warning(f"[VisionSystem] get_latest_frame_packet 未找到相机 {cam_key}")
                return None
            return self._latest_frame_packets.get(cam_key)

    def get_latest_tag36h11_detection_packets(self, cam_key: str) -> Optional[TagDetectionPacket]:
        with self._detection_lock:
            if cam_key not in self._apriltag_36h11_detectors:
                logger.warning(f"[VisionSystem] get_latest_tag36h11_detection_packets 未找到检测器 {cam_key}")
                return None
            return self._latest_detection_packets.get(cam_key)

    # ---------------- 配置 ----------------

    def get_config(self) -> VisionSystemConfig:
        cams = {k: cam.get_config() for k, cam in self._cameras.items()}
        tag36h11_detectors = {k: det.get_config() for k, det in self._apriltag_36h11_detectors.items()}
        return VisionSystemConfig(cameras=cams, tag36h11_detectors=tag36h11_detectors)

    def set_config(self, config: VisionSystemConfig) -> None:
        raise NotImplementedError
    
