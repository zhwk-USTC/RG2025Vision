# map_compose.py
from typing import Iterable, Optional, Tuple, Union, List
import os
import cv2
import numpy as np
import math
from PIL import Image
from .types import TagPose, CarPose

# ---------- 路径与全局资源 ----------
ASSETS_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '../../assets'))
TAG36H11_DIR = os.path.join(ASSETS_DIR, 'apriltag-imgs', 'tag36h11')

FIELD_IMG_PATH = os.path.join(ASSETS_DIR, "field_red.png")
CAR_ICON_PATH = os.path.join(ASSETS_DIR, "car_icon.png")

FIELD_IMG_BASE = Image.open(FIELD_IMG_PATH)
CAR_ICON = None

# ---------- 坐标变换 ----------

PIXEL_PER_METER = 100.0


def world_to_pixel(x_m: float, y_m: float,
                   origin_px: Tuple[float, float], flip_y: bool = True) -> Tuple[float, float]:
    u0, v0 = origin_px
    u = u0 + x_m * PIXEL_PER_METER
    v = v0 - y_m * PIXEL_PER_METER if flip_y else v0 + y_m * PIXEL_PER_METER
    return float(u), float(v)

# ---------- 基础工具 ----------


def _scale_icon(icon: Image.Image, w_px: int, h_px: int) -> Image.Image:
    w, h = max(1, w_px), max(1, h_px)
    return icon.resize((w, h), Image.Resampling.NEAREST)


def _paste_center(dst: Image.Image, src: Image.Image, center_uv: Tuple[float, float]) -> None:
    u, v = center_uv
    dst.alpha_composite(src, dest=(int(round(u - src.width * 0.5)),
                                   int(round(v - src.height * 0.5))))

# ---------- Tag 图像加载 ----------


def _load_tag_rgba(tag_id: int) -> Image.Image:
    """按 ID 加载 Tag PNG"""
    p = os.path.join(TAG36H11_DIR, f'tag36_11_{tag_id:05d}.png')
    return Image.open(p).convert('RGBA')


# ---------- 预合成（一次性烘焙 Tag） ----------

def precompose_field_map(
    image_base: Image.Image,
    tags: List[TagPose],
    origin_px: Tuple[float, float],
    tag_pixel_size: int,
    flip_y: bool = True,
) -> Image.Image:
    """在底图上贴上所有 Tag，并存到 FIELD_IMG"""
    canvas = image_base.copy().convert('RGBA')
    for tag in tags:
        tag_png = _load_tag_rgba(tag.id)
        w = h = tag_pixel_size
        icon = _scale_icon(tag_png, w, h)
        center = world_to_pixel(tag.x, tag.y, origin_px, flip_y)
        _paste_center(canvas, icon, center)

    return canvas

# ---------- 运行时合成（每帧仅叠加小车） ----------


def compose_with_car(
    base_image: Image.Image,
    car: Optional[CarPose],
    *,
    pixels_per_meter: float,
    origin_px: Tuple[float, float],
    car_size_m: Tuple[float, float] = (0.35, 0.25),
    flip_y: bool = True,
) -> Image.Image:
    """在预合成好的 FIELD_IMG 上叠加小车后返回图像"""
    if base_image is None:
        if FIELD_IMG_BASE is None:
            raise RuntimeError(
                'compose_with_car: FIELD_IMG 未准备；请先调用 precompose_field_map(...)')
        canvas = FIELD_IMG_BASE.copy()
    else:
        canvas = Image.open(base_image).convert('RGBA') if isinstance(
            base_image, str) else base_image.convert('RGBA')

    if car is not None:
        if CAR_ICON is None:
            raise RuntimeError(
                'compose_with_car: CAR_ICON 未加载；请先调用 load_car_icon(path)')
        w_px, h_px = car_size_m[0] * \
            pixels_per_meter, car_size_m[1] * pixels_per_meter
        w_px, h_px = int(round(w_px)), int(round(h_px))
        center = world_to_pixel(car.x, car.y, origin_px, flip_y)
        icon = _scale_icon(CAR_ICON, w_px, h_px).rotate(-math.degrees(car.yaw),
                                                        resample=Image.Resampling.NEAREST, expand=True)
        _paste_center(canvas, icon, center)

    return canvas
