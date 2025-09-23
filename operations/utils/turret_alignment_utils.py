"""
炮台水平对准（front 相机）：HSV“灯中心列”对准到目标列
- 检测：VisionUtils.detect_hsv_with_retry（返回像素中心）
- 控制：set_turret_yaw(norm) 绝对位置（-1..1）
- 单调方向由常量 DIRECTION 指定；控制器使用 P（比例）环
"""

import time
from typing import Optional, Literal

from core.logger import logger
from vision import get_vision, CAM_KEY_TYPE
from .vision_utils import VisionUtils
from ..debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory
from .communicate_utils import set_turret_yaw  # norm ∈ [-1, 1]

# ---------------------------
# 可调参数
# ---------------------------

# 方向常量：1 表示 norm↑→像素列↑；-1 表示 norm↑→像素列↓
DIRECTION = 1

PIX_TOL = 3          # 对齐像素容差
SETTLE_SEC = 0.1     # 单步后额外稳定等待（set_turret_yaw内部已有1秒等待）
MAX_ITERS = 60
MAX_RETRIES_PER_ITER = 10

# —— P 控制参数（把像素误差映射为归一化步进）——
KP = 0.8                 # 比例增益（对误差/图像宽度的系数）
MAX_STEP_NORM = 0.20     # 单步最大归一化步进
MIN_STEP_NORM = 0.01     # 单步最小归一化步进（避免死区）
SMALL_ERR_FRAC = 0.01    # 小误差区(相当于 1% 画面宽度)时允许更小步进，减抖

def _get_width(cam_key: CAM_KEY_TYPE) -> int:
    vis = get_vision()
    if vis and hasattr(vis, '_cameras'):
        cam = vis._cameras.get(cam_key)
        if cam and hasattr(cam, 'width') and cam.width is not None:
            return int(cam.width)
        elif cam and hasattr(cam, 'frame_size'):
            size = getattr(cam, "frame_size", None)
            if size and len(size) >= 2:
                return int(size[0])
    return 1920

def _target_to_px(target_column, width: int) -> float:
    if isinstance(target_column, (int, float)) and target_column > 1.0:
        return float(target_column)
    t = max(0.0, min(1.0, float(target_column)))
    return t * (width - 1)

def _measure_u_px(
    cam_key, max_retries, debug_prefix, task_name
) -> Optional[float]:
    det, _ = VisionUtils.detect_hsv_with_retry(
        cam_key=cam_key,
        max_retries=max_retries,
        interval_sec=0.03,
        debug_prefix=debug_prefix,
        task_name=task_name
    )
    if det is None:
        return None
    
    # HSV 返回中心像素坐标 - 安全地获取中心点的x坐标
    center = getattr(det, 'center', None)
    if center is not None and len(center) >= 2:
        return float(center[0])
    
    # 备用属性检查
    center_px = getattr(det, 'center_px', None)
    if center_px is not None and len(center_px) >= 2:
        return float(center_px[0])
    
    # 如果有 u 属性
    u = getattr(det, 'u', None)
    if u is not None:
        return float(u)
    
    return None

def _clamp_norm(x: float) -> float:
    return max(-1.0, min(1.0, float(x)))

def turret_align_front_to_light_column(
    *,
    cam_key: Literal["front"] = "front",
    target_column: float = 0.5,         # 0~1 归一化 或 像素列(>1)
    pixel_tolerance: int = PIX_TOL,
    start_norm: float = 0.0,
    debug_prefix: str = "turret_align",
    task_name: str = "TurretAlignToLight"
) -> bool:
    width = _get_width(cam_key)
    target_px = _target_to_px(target_column, width)

    cur_norm = _clamp_norm(start_norm)
    set_turret_yaw(cur_norm)
    time.sleep(SETTLE_SEC)

    for it in range(MAX_ITERS):
        u_px = _measure_u_px(cam_key, MAX_RETRIES_PER_ITER, debug_prefix, task_name)
        if u_px is None:
            set_debug_var(f"{debug_prefix}_status", "no_detection",
                          DebugLevel.WARNING, DebugCategory.STATUS, "未检测到灯")
            return False

        pix_err = u_px - target_px           # 像素误差（右正左负）
        if abs(pix_err) <= float(pixel_tolerance):
            set_debug_var(f"{debug_prefix}_status", "done",
                          DebugLevel.SUCCESS, DebugCategory.STATUS, "炮台已对准目标列")
            logger.info(f"[{task_name}] 对齐完成 |pix_err|={abs(pix_err):.1f}")
            return True

        # -------- P 控制：像素误差 → 归一化步进 --------
        frac_err = pix_err / float(width)    # 归一化到画面宽度（-1..1 范围内的一小段）
        raw_step = - DIRECTION * KP * frac_err

        # 小误差区允许更细小步进以防抖；大误差区给最小步进避免死区
        mag = abs(raw_step)
        if abs(frac_err) > SMALL_ERR_FRAC:
            mag = max(mag, MIN_STEP_NORM)
        # 限幅
        mag = min(mag, MAX_STEP_NORM)
        step = (raw_step / (abs(raw_step) + 1e-12)) * mag  # 恢复符号并应用幅值

        # 更新并下发
        cur_norm = _clamp_norm(cur_norm + step)
        set_turret_yaw(cur_norm)

        # 调试信息
        set_debug_var(f"{debug_prefix}_loop",
                      {
                          "iter": it + 1,
                          "u_px": round(u_px, 2),
                          "pix_err": round(pix_err, 2),
                          "frac_err": round(frac_err, 5),
                          "raw_step": round(raw_step, 5),
                          "step": round(step, 5),
                          "cur_norm": round(cur_norm, 5)
                      },
                      DebugLevel.INFO, DebugCategory.CONTROL, "P 控制一步")
        time.sleep(SETTLE_SEC)

    set_debug_var(f"{debug_prefix}_status", "max_iters",
                  DebugLevel.WARNING, DebugCategory.STATUS, "达到最大迭代次数仍未对齐")
    logger.warning(f"[{task_name}] 达到最大迭代次数({MAX_ITERS})，未完成对齐")
    return False
