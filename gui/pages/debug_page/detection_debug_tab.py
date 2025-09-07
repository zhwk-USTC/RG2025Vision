from nicegui import ui
import asyncio
import numpy as np
from PIL import Image
from typing import Optional, Union

from vision import get_vision, save_vision_config
from vision.camera import Camera
from vision.detection.apriltag import Tag36h11Detector
from core.logger import logger


def np_to_pil(img_np):
    if img_np is None:
        return get_empty_img()
    if isinstance(img_np, Image.Image):
        return img_np
    return Image.fromarray(img_np.astype('uint8'), 'RGB')

def get_tag36h11_debug_img():
    try:
        img = Image.open("assets\\apriltag-imgs\\tag36h11\\tag36_11_00000.png")
        # 缩放到 400x400 像素，使用最近邻插值
        img_resized = img.resize((400, 400), Image.Resampling.NEAREST)
        return img_resized
    except Exception as e:
        logger.warning(f"无法加载调试图片: {e}")
        return get_empty_img()

def get_empty_img():
    return Image.new("RGB", (640, 480), (200, 200, 200))


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


def render_detection_block(key:str,cam: Camera):
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
                vs._update_frames(keys=key)
                raw_frame_packet = vs.get_latest_frame_packet(key)
                processed_raw_img = prepare_image_for_display(raw_frame_packet.img_bgr if raw_frame_packet else None)
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


def render_detection_debug_tab():
    vs = get_vision()
    def on_save_config():
        save_vision_config()
    def on_connect_all():
        vs.start()
    def on_disconnect_all():
        vs.stop()
    with ui.row():
        ui.interactive_image(get_tag36h11_debug_img())
    with ui.row().classes('q-gutter-md q-mb-md'):

        ui.button('连接所有摄像头', color='primary', on_click=on_connect_all)
        ui.button('断开所有摄像头', color='negative', on_click=on_disconnect_all)

    for key, detector in vs._apriltag_36h11_detectors.items():
        render_tag36h11_block(key)

def render_tag36h11_block(key: str):
    
    header_state = {'text': ''}

    def _header_text() -> str:
        alias = key or '未命名'
        name = 'tag36h11'
        return f'{alias} · {name}'

    def _refresh_header():
        header_state['text'] = _header_text()
    _refresh_header()
    with ui.expansion(value=False).classes('w-full q-mb-md') as exp:
        # 自定义 header（图标 + 动态标题）
        with exp.add_slot('header'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('qr_code')
                ui.label().bind_text_from(header_state, 'text')
        with ui.row().classes('items-center q-gutter-md'):
            vs = get_vision()
            ui.label(f"{key}").classes('text-h6')

            def on_connect_click():
                vs._cameras[key].connect()

            def on_disconnect_click():
                vs._cameras[key].disconnect()
            connect_btn = ui.button(
                '连接', color='primary', on_click=on_connect_click)
            disconnect_btn = ui.button(
                '断开', color='negative', on_click=on_disconnect_click)

            _debug_loop = None
            def _detect_and_update():
                vs._update_frames(keys=key)
                vs._detect_tag36h11(keys=key)
                
                detection_result_packet = vs.get_latest_tag36h11_detection_packets(key)
                if detection_result_packet is None:
                    logger.warning(f"[DetectionDebugTab] 未获取到 {key} 的检测结果包")
                    raw_image = None
                    detection_result = None
                else:
                    raw_image = detection_result_packet.img_bgr
                    detection_result = detection_result_packet.dets
                processed_raw_img = prepare_image_for_display(raw_image)
                overlay_img = Tag36h11Detector.draw_overlay(raw_image, detection_result)
                processed_overlay_img = prepare_image_for_display(overlay_img)
                img_widget.set_source(processed_raw_img)
                overlay_widget.set_source(processed_overlay_img)
                detection_result_text = Tag36h11Detector.get_result_text(detection_result)
                detection_result_widget.set_content('检测结果：\n'+detection_result_text)
            def on_debug_change(value):
                nonlocal _debug_loop
                if value:
                    _debug_loop = ui.timer(1.0 / debug_fps_input.value, _detect_and_update)
                    logger.info(f"已启动模拟检测循环，频率 {debug_fps_input.value} FPS")
                else:
                    if _debug_loop:
                        _debug_loop.cancel()
                        logger.info("已停止模拟检测循环")
            debug_btn = ui.checkbox('模拟检测循环', on_change=lambda e: on_debug_change(e.value))
            debug_fps_input = ui.number('帧率', value=30, min=1, max=30, step=1)
        with ui.row().classes('q-gutter-sm'):
            with ui.column().classes('q-gutter-sm'):
                ui.label('原图').classes('text-subtitle2')
                img_widget = ui.interactive_image(get_empty_img())

            with ui.column().classes('q-gutter-sm'):
                ui.label('检测叠加').classes('text-subtitle2')
                overlay_widget = ui.interactive_image(get_empty_img())

            detection_result_widget = ui.code('').props('readonly')

    
