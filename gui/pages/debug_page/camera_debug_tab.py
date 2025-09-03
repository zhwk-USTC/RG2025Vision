from nicegui import ui
import asyncio
import numpy as np
from PIL import Image
from typing import Optional, Union

from vision import get_vision, save_vision_config
from vision.camera_node import CameraNode
from core.logger import logger


def np_to_pil(img_np):
    if img_np is None:
        return get_empty_img()
    if isinstance(img_np, Image.Image):
        return img_np
    return Image.fromarray(img_np.astype('uint8'), 'RGB')


def get_empty_img():
    return Image.new("RGB", (640, 480), (200, 200, 200))


def prepare_image_for_display(img_np):
    """将numpy数组或PIL图像转换为适合显示的PIL格式"""
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


def render_camera_block(cam_node: CameraNode):
    with ui.card().classes('q-pa-md q-mb-md'):
        with ui.row().classes('items-center q-gutter-md'):
            ui.label(f"{cam_node.alias}").classes('text-h6')

            def on_connect_click():
                cam_node.start()

            def on_disconnect_click():
                cam_node.stop()
            connect_btn = ui.button(
                '连接', color='primary', on_click=on_connect_click)
            disconnect_btn = ui.button(
                '断开', color='negative', on_click=on_disconnect_click)

            _debug_loop = None
            def on_debug_change(value):
                nonlocal _debug_loop
                if value:
                    _debug_loop = ui.timer(1.0 / debug_fps_input.value, cam_node.read_frame_and_detect_async)
                    logger.info(f"已启动模拟检测循环，频率 {debug_fps_input.value} FPS")
                else:
                    if _debug_loop:
                        _debug_loop.cancel()
                        logger.info("已停止模拟检测循环")
            debug_btn = ui.checkbox('模拟检测循环', on_change=lambda e: on_debug_change(e.value))
            debug_fps_input = ui.number('帧率', value=30, min=1, max=30, step=1)
        with ui.row().classes('q-gutter-sm q-mt-md'):
            ui.label('检测叠加类型:').classes('text-subtitle2')
            overlay_type = 'none'
            overlay_options = ['none', 'tag36h11']
            def on_overlay_change(value):
                overlay_type = value

            overlay_radio = ui.radio(overlay_options, value='tag36h11', on_change=on_overlay_change).props('inline')

        with ui.row().classes('q-gutter-sm'):
            with ui.column().classes('q-gutter-sm'):
                ui.label('原图').classes('text-subtitle2')
                img_widget = ui.interactive_image(get_empty_img())

            with ui.column().classes('q-gutter-sm'):
                ui.label('检测叠加').classes('text-subtitle2')
                overlay_widget = ui.interactive_image(get_empty_img())

            cam_status_widget = ui.code('').props('readonly')
            detection_result_widget = ui.code('').props('readonly')
    
    def update_imgs():
        raw_frame = cam_node.latest_frame
        match overlay_type:
            case 'none':
                overlay_frame = raw_frame
            case 'tag36h11':
                overlay_frame = cam_node._tag36h11_detector.draw_overlay(raw_frame, cam_node.latest_tag36h11_detection)
            case _:
                logger.warning(f"未知的 overlay_type: {overlay_type}")
                overlay_frame = raw_frame
        processed_raw_img = prepare_image_for_display(raw_frame)
        processed_overlay_img = prepare_image_for_display(overlay_frame)
        img_widget.set_source(processed_raw_img)
        overlay_widget.set_source(processed_overlay_img)
        cam_status_text = cam_node.status
        cam_status_widget.set_content('摄像头状态：\n'+cam_status_text)
        detection_result_text = cam_node._tag36h11_detector.get_result_text(cam_node.latest_tag36h11_detection) if cam_node._tag36h11_detector else "未启用检测器"
        detection_result_widget.set_content('检测结果：\n'+detection_result_text)

    ui.timer(1.0/5, update_imgs)


def render_camera_tab():
    vs = get_vision()
    def on_save_config():
        save_vision_config()
    def on_connect_all():
        vs.start()
    def on_disconnect_all():
        vs.stop()
    with ui.row().classes('q-gutter-md q-mb-md'):
        ui.button('连接所有摄像头', color='primary', on_click=on_connect_all)
        ui.button('断开所有摄像头', color='negative', on_click=on_disconnect_all)
        ui.button('保存配置', color='secondary', on_click=on_save_config)

    for cam in vs._cam_nodes:
        render_camera_block(cam)

    
