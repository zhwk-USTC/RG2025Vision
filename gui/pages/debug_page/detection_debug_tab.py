from nicegui import ui
import numpy as np
from PIL import Image, ImageDraw
from typing import Optional, Union

from vision import get_vision
from vision.camera import Camera
from vision.detection import Tag36h11Detector, Tag25h9Detector, HSVDetector
from core.logger import logger


# ---------------- 工具函数 ----------------

def np_to_pil(img_np):
    if img_np is None:
        return get_empty_img()
    if isinstance(img_np, Image.Image):
        return img_np
    return Image.fromarray(img_np.astype('uint8'), 'RGB')


def get_tag36h11_debug_img():
    try:
        img = Image.open("assets\\apriltag-imgs\\tag36h11\\tag36_11_00000.png")
        return img.resize((300, 300), Image.Resampling.NEAREST)
    except Exception as e:
        logger.warning(f"无法加载调试图片: {e}")
        return get_empty_img()

def get_tag25h9_debug_img():
    try:
        img = Image.open("assets\\apriltag-imgs\\tag25h9\\tag25_09_00000.png")
        return img.resize((300, 300), Image.Resampling.NEAREST)
    except Exception as e:
        logger.warning(f"无法加载tag25h9调试图片: {e}")
        return get_empty_img()

def get_green_dot_debug_img(size: int = 300, radius: int = 15,
                            color=(0, 255, 0), bg=(0, 0, 0)) -> Image.Image:
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(bbox, fill=color, outline=None)
    return img

def get_empty_img():
    return Image.new("RGB", (320, 240), (200, 200, 200))

def prepare_image_for_display(img_np: Optional[Union[np.ndarray, Image.Image]]) -> Image.Image:
    """将numpy数组或PIL图像转换为适合显示的PIL格式"""
    if img_np is None:
        return get_empty_img()
    pil_img = np_to_pil(img_np)
    max_width = 320
    if pil_img.width > max_width:
        ratio = max_width / pil_img.width
        pil_img = pil_img.resize((max_width, int(pil_img.height * ratio)))
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
    return pil_img


# ---------------- 相机检测块（每个摄像头一个）----------------

def render_detection_block(key: str, cam: Camera):
    vs = get_vision()

    with ui.card().classes('q-pa-sm q-mb-sm'):
        with ui.row().classes('items-center gap-2'):
            ui.icon('videocam')
            ui.label(f'{key}').classes('text-subtitle1')

            def on_connect_click():
                cam.connect()
                status_widget.set_content('摄像头状态：\n' + cam.get_status())

            def on_disconnect_click():
                cam.disconnect()
                status_widget.set_content('摄像头状态：\n' + cam.get_status())

            ui.button('连接', color='primary', on_click=on_connect_click)
            ui.button('断开', color='negative', on_click=on_disconnect_click)

            # 检测模式下拉框：不检测 / Tag36h11 / HSV
            mode_state = {'mode': 'none'}  # none | tag36h11 | tag25h9 | hsv
            mode_options = {
                'none': '不检测',
                'tag36h11': 'AprilTag 36h11',
                'tag25h9': 'AprilTag 25h9',
                'hsv': 'HSV 颜色',
            }
            def on_mode_change(v):
                mode_state['mode'] = v or 'none'
                ui.notify(f'{key} 检测模式: {mode_options[mode_state["mode"]]}', color='primary')

            ui.select(
                options=mode_options,
                value='none',
                label='检测模式',
                on_change=lambda e: on_mode_change(e.value),
            ).classes('w-40')

            # 更新循环
            _debug_loop = {}
            debug_fps_input = ui.number('FPS', value=5, min=1, max=60, step=1).classes('w-24')

            def _tick():
                # 1) 抓帧
                raw_img = vs.read_frame(key=key) # type: ignore

                overlay_img = raw_img
                result_text = '（未进行检测）'

                # 2) 依据选择的模式执行检测
                if mode_state['mode'] == 'tag36h11':
                    intrinsics = vs.get_camera_intrinsics(key) # type: ignore
                    dets = vs.detect_tag36h11(raw_img, intrinsics)
                    overlay_img = Tag36h11Detector.draw_overlay(raw_img, dets)
                    result_text = Tag36h11Detector.get_result_text(dets)
                elif mode_state['mode'] == 'tag25h9':
                    intrinsics = vs.get_camera_intrinsics(key) # type: ignore
                    dets = vs.detect_tag25h9(raw_img, intrinsics)
                    overlay_img = Tag25h9Detector.draw_overlay(raw_img, dets)
                    result_text = Tag25h9Detector.get_result_text(dets)
                elif mode_state['mode'] == 'hsv':
                    dets = vs.detect_hsv(raw_img)
                    overlay_img = HSVDetector.draw_overlay(raw_img, dets)
                    result_text = HSVDetector.get_result_text(dets)

                # 3) 显示
                img_widget.set_source(prepare_image_for_display(raw_img))
                overlay_widget.set_source(prepare_image_for_display(overlay_img))
                detection_result_widget.set_content('检测结果：\n' + (result_text or ''))

                # 4) 状态
                status_widget.set_content('摄像头状态：\n' + cam.get_status())

            def on_loop_toggle(enabled: bool):
                if enabled:
                    fps = int(debug_fps_input.value or 5)
                    _debug_loop['timer'] = ui.timer(1.0 / max(1, fps), _tick)
                    logger.info(f'[{key}] 更新循环启动：{fps} FPS')
                else:
                    if _debug_loop['timer']:
                        _debug_loop['timer'].cancel()
                        _debug_loop['timer'] = None
                        logger.info(f'[{key}] 更新循环已停止')

            ui.checkbox('更新循环', value=False, on_change=lambda e: on_loop_toggle(bool(e.value)))

        # 画面与文本
        with ui.row().classes('q-gutter-sm'):
            with ui.column().classes('q-gutter-xs'):
                ui.label('原图').classes('text-caption')
                img_widget = ui.interactive_image(get_empty_img()).classes('rounded-borders')

            with ui.column().classes('q-gutter-xs'):
                ui.label('叠加').classes('text-caption')
                overlay_widget = ui.interactive_image(get_empty_img()).classes('rounded-borders')

            with ui.column().classes('q-gutter-xs'):
                ui.label('状态 / 结果').classes('text-caption')
                status_widget = ui.code(cam.get_status()).props('readonly dense').classes('w-64')
                detection_result_widget = ui.code('').props('readonly dense').classes('w-64')


# ---------------- 页面入口 ----------------

def render_detection_debug_tab():
    vs = get_vision()

    # 顶部：全局示例与批量控制（可选）
    with ui.row().classes('q-gutter-xl'):
        with ui.column().classes('items-start'):
            ui.label('Tag36h11 示例').classes('text-subtitle2')
            ui.interactive_image(get_tag36h11_debug_img())
        with ui.column().classes('items-start'):
            ui.label('Tag25h9 示例').classes('text-subtitle2')
            ui.interactive_image(get_tag25h9_debug_img())
        with ui.column().classes('items-start'):
            ui.label('绿色圆点示例').classes('text-subtitle2')
            ui.interactive_image(get_green_dot_debug_img())

    # 为每个摄像头渲染一个检测块 + 下拉选择检测
    for key, cam in vs._cameras.items():
        render_detection_block(key, cam)
