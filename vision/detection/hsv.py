# vision/detection/hsv.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
import numpy as np
import cv2

from core.logger import logger

@dataclass(slots=True)
class HSVDetectConfig:
    # HSV 阈值（OpenCV: H ∈ [0..179], S/V ∈ [0..255]）
    h_min: int = 40
    h_max: int = 90
    s_min: int = 80
    v_min: int = 180

    # 亮绿色优势：G / max(R,B) >= ratio
    g_dom_ratio: float = 1.2
    g_min: int = 180

    # 形态与筛选
    min_area: int = 3
    max_area: int = 400
    circularity_min: float = 0.5
    open_kernel: int = 3  # 形态学开运算核尺寸（<=1 则不做）

    # 输出数量限制（0 或负数=不限）
    max_results: int = 0

@dataclass(slots=True)
class HSVDetection:
    center: Tuple[float, float]     # (cx, cy)
    radius: float                  # 近似半径（由最小外接圆得到）
    area: int                      # 连通域像素数
    peak: int                      # ROI 内峰值（G 通道）
    mean: float                    # ROI 内平均 G
    score: float                   # 置信度（简单：峰值 * 圆度）
    contour: Optional[np.ndarray]  # 原始轮廓 (N,1,2) int32
    bbox: Tuple[int, int, int, int]# (x,y,w,h)

class HSVDetector:
    """简易 HSV 斑点检测器（用于明亮绿色点光源等）"""

    def __init__(self, config: Optional[HSVDetectConfig] = None) -> None:
        self.config = config or HSVDetectConfig()

    def update_config(self, cfg: HSVDetectConfig) -> None:
        self.config = cfg
        logger.info(f"[HSVDetector] 配置已更新: {self.config}")

    # --------- 主检测 ---------
    def detect(self, image: np.ndarray) -> Optional[List[HSVDetection]]:
        """
        输入: BGR 或 RGB 或灰度（自动处理），输出: HSVDetection 列表（可能为空列表）
        返回 None 表示输入非法。
        """
        if image is None or image.size == 0:
            return None

        img = np.asarray(image)
        if img.ndim == 2:  # 灰度 -> 伪 BGR
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4:  # BGRA -> BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # 若可能是 RGB，则尝试快速启发式判断；否则默认当作 BGR
        # 这里保守处理：直接认为是 BGR（与你相机流一致）。如需支持 RGB，可暴露开关。
        bgr = img

        cfg = self.config
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        H, S, V = cv2.split(hsv)
        B, G, R = cv2.split(bgr)

        # 颜色/亮度掩码
        mask_h = cv2.inRange(H, np.array(cfg.h_min, dtype=H.dtype), np.array(cfg.h_max, dtype=H.dtype))
        mask_s = cv2.inRange(S, np.array(cfg.s_min, dtype=S.dtype), np.array(255, dtype=S.dtype))
        mask_v = cv2.inRange(V, np.array(cfg.v_min, dtype=V.dtype), np.array(255, dtype=V.dtype))
        mask_color = cv2.bitwise_and(mask_h, cv2.bitwise_and(mask_s, mask_v))

        # 绿色优势
        max_rb = cv2.max(R, B).astype(np.float32)
        g_dom = (G.astype(np.float32) / np.maximum(max_rb, 1.0)) >= float(cfg.g_dom_ratio)
        mask_gmin = (G >= int(cfg.g_min))
        mask_green_dom = (g_dom & mask_gmin).astype(np.uint8) * 255

        mask = cv2.bitwise_and(mask_color, mask_green_dom)

        if cfg.open_kernel and cfg.open_kernel > 1:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (cfg.open_kernel, cfg.open_kernel))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)

        # 连通域
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        dets: List[HSVDetection] = []

        for lbl in range(1, num_labels):
            x, y, w, h, area = stats[lbl]
            if area < cfg.min_area or area > cfg.max_area:
                continue

            comp_mask = (labels == lbl).astype(np.uint8)
            contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            cnt = contours[0]
            perim = cv2.arcLength(cnt, True)
            if perim <= 0:
                continue
            circularity = 4.0 * np.pi * (float(area) / (perim * perim))
            if circularity < cfg.circularity_min:
                continue

            (cx, cy), radius = cv2.minEnclosingCircle(cnt)
            # 统计绿色强度
            roi_mask = comp_mask[y:y+h, x:x+w] > 0
            g_roi = G[y:y+h, x:x+w][roi_mask]
            mean_g = float(np.mean(np.asarray(g_roi, dtype=np.float32))) if g_roi.size else 0.0
            peak_g = int(np.max(g_roi)) if g_roi.size else 0
            score = float(peak_g / 255.0) * float(np.clip(circularity, 0, 1))

            dets.append(HSVDetection(
                center=(float(cx), float(cy)),
                radius=float(radius),
                area=int(area),
                peak=peak_g,
                mean=mean_g,
                score=score,
                contour=cnt,
                bbox=(int(x), int(y), int(w), int(h)),
            ))

        # 排序&截断
        dets.sort(key=lambda d: d.score, reverse=True)
        if self.config.max_results and self.config.max_results > 0:
            dets = dets[: self.config.max_results]
        return dets

    # --------- 可视化 ---------
    @staticmethod
    def draw_overlay(img: Optional[np.ndarray], detect_result: Optional[List[HSVDetection]]) -> Optional[np.ndarray]:
        if img is None or detect_result is None:
            return None
        overlay = np.asarray(img).copy()

        H, W = overlay.shape[:2]
        diag = float(np.hypot(H, W))
        line_th   = max(2, int(diag / 200))
        font_scale = max(0.5, diag / 400)
        font_th    = max(2, int(diag / 220))

        red = (255, 0, 0)  # BGR: 红色

        for i, det in enumerate(detect_result):
            c = (int(round(det.center[0])), int(round(det.center[1])))
            r = max(2, int(round(det.radius)))

            # 圆与中心点：红色
            cv2.circle(overlay, c, r, red, line_th, cv2.LINE_AA)
            cv2.circle(overlay, c, 2, red, -1, cv2.LINE_AA)

            # 文字：红色
            label = f"#{i} peak={det.peak} area={det.area}"
            cv2.putText(overlay, label, (c[0] + 6, c[1] - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, red, font_th, cv2.LINE_AA)

        return overlay

    # --------- 文本结果 ---------
    @staticmethod
    def get_result_text(detect_result: Optional[List[HSVDetection]]) -> str:
        if detect_result is None:
            return "无检测结果"
        if len(detect_result) == 0:
            return "未检测到目标"
        lines = []
        for i, d in enumerate(detect_result):
            lines.append(
                f"#{i}: center=({d.center[0]:.1f},{d.center[1]:.1f}), r={d.radius:.1f}, "
                f"area={d.area}, peak={d.peak}, mean={d.mean:.1f}, score={d.score:.3f}"
            )
        return "\n".join(lines)

    def get_config(self) -> HSVDetectConfig:
        return self.config
