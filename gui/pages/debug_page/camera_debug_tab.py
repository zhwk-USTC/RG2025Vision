from nicegui import ui
import asyncio
import numpy as np
from PIL import Image
from typing import Optional, Union

from vision import get_vision, save_vision_config
from vision.camera import Camera
from core.logger import logger


def np_to_pil(img_np):
    if img_np is None:
        return get_empty_img()
    if isinstance(img_np, Image.Image):
        return img_np
    return Image.fromarray(img_np.astype('uint8'), 'RGB')


def get_empty_img():
    return Image.new("RGB", (320,240), (200, 200, 200))


def prepare_image_for_display(img_np: Optional[Union[np.ndarray, Image.Image]]) -> Image.Image:
    """将numpy数组或PIL图像转换为适合显示的PIL格式"""
    if img_np is None:
        return get_empty_img()
    
     # 转换为PIL图像
    pil_img = np_to_pil(img_np)

    # 缩放到最大宽度 320px
    max_width = 320
    if pil_img.width > max_width:
        ratio = max_width / pil_img.width
        new_size = (max_width, int(pil_img.height * ratio))
        pil_img = pil_img.resize(new_size)

    # 转换为RGB格式（如果需要）
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')

    return pil_img


def render_camera_block(key:str,cam: Camera):
    with ui.card().classes('q-pa-md q-mb-md'):
        with ui.row().classes('items-center q-gutter-md'):
            ui.label(f"{key}").classes('text-h6')

            def on_connect_click():
                cam.connect()

            def on_disconnect_click():
                cam.disconnect()
            connect_btn = ui.button(
                '连接', color='primary', on_click=on_connect_click)
            disconnect_btn = ui.button(
                '断开', color='negative', on_click=on_disconnect_click)

            _debug_loop = None
            def _read_and_update_frame():
                vs = get_vision()
                frame = vs.read_frame(key=key)  # type: ignore
                processed_raw_img = prepare_image_for_display(frame)
                img_widget.set_source(processed_raw_img)
                cam_status_text = cam.get_status()
                cam_status_widget.set_content('摄像头状态：\n'+cam_status_text)
            def on_debug_change(value):
                nonlocal _debug_loop
                if value:
                    _debug_loop = ui.timer(1.0 / debug_fps_input.value, _read_and_update_frame)
                    logger.info(f"已启动更新循环，频率 {debug_fps_input.value} FPS")
                else:
                    if _debug_loop:
                        _debug_loop.cancel()
                        logger.info("已停止更新循环")
            debug_btn = ui.checkbox('更新循环', on_change=lambda e: on_debug_change(e.value))
            debug_fps_input = ui.number('帧率', value=30, min=1, max=30, step=1)
        with ui.row().classes('q-gutter-sm'):
            with ui.column().classes('q-gutter-sm'):
                ui.label('原图').classes('text-subtitle2')
                img_widget = ui.interactive_image(get_empty_img())

            cam_status_widget = ui.code('').props('readonly')


def render_camera_debug_tab():
    vs = get_vision()

    for key, cam in vs._cameras.items():
        render_camera_block(key, cam)
