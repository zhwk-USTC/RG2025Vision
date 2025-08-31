import asyncio
import time
import numpy as np
from typing import Dict, Iterable, List, Optional, Tuple

from core.logger import logger
from ..nodes import CameraNode
from ..detection.apriltag import TagDetections, TagDetectionConfig, Tag36h11Detector
from ..camera import scan_cameras
from ..types import CamNodeConfig, VisionSystemConfig

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
        cam_num: int
    ) -> None:
        scan_cameras()
        self._nodes: List[CameraNode] = []
        for i in range(cam_num):
            self._nodes.append(CameraNode())
        logger.info(f"[VisionSystem] 已注册相机节点：{', '.join([n.alias for n in self._nodes])}")

    # ---------------- 基本操作 ----------------
    def start(self) -> bool:
        """
        连接所有相机
        返回是否全部成功。
        """
        ok_all = True
        for node in self._nodes:
            try:
                ok = node.start()
                ok_all = ok_all and ok
            except Exception as e:
                logger.warning(f"[VisionSystem] 启动节点失败 {node.alias}: {e}")
                ok_all = False
        return ok_all

    def stop(self) -> None:
        for node in self._nodes:
            try:
                node.stop()
            except Exception as e:
                logger.warning(f"[VisionSystem] 停止节点异常: {e}")

    def close(self) -> None:
        """彻底关闭（含节点线程池）"""
        for node in self._nodes:
            try:
                node.close()
            except Exception as e:
                logger.warning(f"[VisionSystem] 关闭节点异常: {e}")

    # ---------------- 同步更新 ----------------
    def update(self) -> List[Optional[TagDetections]]:
        """
        同步（阻塞）调用所有相机进行一次联合定位检测
        """
        logger.info("[VisionSystem] 开始同步更新所有相机的检测")

        # 创建检测任务列表
        tasks = [
            node.read_frame_and_detect()
            for node in self._nodes
        ]

        # 使用 asyncio.run() 来运行异步任务并同步等待结果
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

        # 处理结果
        out: List[Optional[TagDetections]] = []
        for node, res in zip(self._nodes, results):
            alias = node.alias
            if isinstance(res, BaseException):
                logger.warning(f"[VisionSystem] detect_once {alias} 异常: {res}")
                res = None
            out.append(res)
        
        logger.info("[VisionSystem] 所有相机检测完成")
        return out

    # ---------------- 读取最近检测 ----------------
    def get_latest_frames(self) -> List[Optional[np.ndarray]]:
        """
        同步读取多个相机缓存的最近帧（不触发新检测）。
        """
        out: List[Optional[np.ndarray]] = []
        for node in self._nodes:
            try:
                frame = node.latest_frame 
                out.append(frame)
            except Exception as e:
                logger.warning(f"[VisionSystem] latest_frame {node.alias} 异常: {e}")
                out.append(None)
        return out

    def get_latest_tag36h11_detections(self) -> List[Optional[TagDetections]]:
        """
        同步读取多个相机缓存的最近检测结果（不触发新检测）。
        """
        out: List[Optional[TagDetections]] = []
        for node in self._nodes:
            try:
                tags = node.latest_tag36h11_detection  # 假设这是同步读取的方法
                out.append(tags)
            except Exception as e:
                logger.warning(f"[VisionSystem] latest_tags {node.alias} 异常: {e}")
                out.append(None)
        return out

    # ---------------- 配置 ----------------
    
    def get_config(self) -> VisionSystemConfig:
        configs: List[CamNodeConfig] = []
        try:
            for node in self._nodes:
                config = node.get_config()
                configs.append(config)
        except Exception as e:
            logger.warning(f"[VisionSystem] 导出配置异常: {e}")
            return VisionSystemConfig()
        return VisionSystemConfig(cam_nodes=configs)

    def set_config(self, config: VisionSystemConfig) -> None:
        cam_node_configs = config.cam_nodes
        try:
            for node, cam_config in zip(self._nodes, cam_node_configs):
                node.set_config(cam_config)
        except Exception as e:
            logger.warning(f"[VisionSystem] 设置节点配置异常: {e}")
