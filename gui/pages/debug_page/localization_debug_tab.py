from typing import Optional, Union
import numpy as np
from PIL import Image
from nicegui import ui
from core.logger import logger
from vision import get_vision
from vision.detection import Tag36h11Detector

# ---------------------------
# 工具
# ---------------------------
def _deg(rad: float) -> float:
    try:
        return float(np.degrees(rad))
    except Exception:
        return 0.0

def np_to_pil(img_np):
    if img_np is None:
        return get_empty_img()
    if isinstance(img_np, Image.Image):
        return img_np
    return Image.fromarray(img_np.astype('uint8'), 'RGB')

def get_empty_img():
    return Image.new("RGB", (640, 480), (200, 200, 200))

def get_tag36h11_debug_img():
    try:
        img = Image.open("assets\\apriltag-imgs\\tag36h11\\tag36_11_00000.png")
        return img.resize((400, 400), Image.Resampling.NEAREST)
    except Exception as e:
        logger.warning(f"无法加载调试图片: {e}")
        return get_empty_img()

def prepare_image_for_display(img_np: Optional[Union[np.ndarray, Image.Image]]) -> Image.Image:
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

# ---------------------------
# 入口：定位测试页（单相机选择）
# ---------------------------
def render_localization_tab() -> None:
    vs = get_vision()

    ui.label('定位模块测试').classes('text-h6')
    with ui.row().classes('q-gutter-xl'):
        with ui.column().classes('items-start'):
            ui.label('Tag36h11 示例').classes('text-subtitle2')
            ui.interactive_image(get_tag36h11_debug_img())
    # 相机选择下拉
    cam_keys = list(vs._cameras.keys())
    state = {'cam_key': cam_keys[0] if cam_keys else None}
    row = ui.row().classes('items-center gap-2')
    with row:
        ui.label('相机').classes('text-caption')
        cam_select = ui.select(
            options={k: k for k in cam_keys},
            value=state['cam_key'],
            on_change=lambda e: _on_cam_change(e.value),
        ).classes('w-48')

    # 容器：根据选择的相机渲染一个 block
    block_container = ui.column().classes('q-gutter-sm')

    # 计时器句柄放外层，切相机时可关闭
    timers = {'timer': None}

    def _on_cam_change(new_key: Optional[str]):
        # 停掉旧的定时器
        if timers['timer']:
            timers['timer'].cancel()
            timers['timer'] = None
        # 清空容器并重建块
        block_container.clear()
        state['cam_key'] = new_key
        if new_key:
            render_localization_block(new_key, timers, parent=block_container)

    # 初次渲染
    _on_cam_change(state['cam_key'])


# ---------------------------
# 单相机定位测试块
# ---------------------------
def render_localization_block(key: str, timers: dict, parent=None):
    vs = get_vision()
    cam = vs._cameras.get(key, None)

    container = parent if parent is not None else ui.column()
    with container:
        with ui.card().classes('q-pa-sm q-mb-sm'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('videocam')
                ui.label(f'{key}').classes('text-subtitle1')

                def on_connect_click():
                    if cam:
                        cam.connect()
                        status_widget.set_content('摄像头状态：\n' + cam.get_status())

                def on_disconnect_click():
                    if cam:
                        cam.disconnect()
                        status_widget.set_content('摄像头状态：\n' + cam.get_status())

                ui.button('连接', color='primary', on_click=on_connect_click)
                ui.button('断开', color='negative', on_click=on_disconnect_click)

                # 目标 tag id（可选；不填则选最近的）
                ui.label('Tag ID').classes('text-caption')
                tag_id_input = ui.number('', value=None, min=0, step=1).classes('w-24')

                # 更新循环
                debug_fps_input = ui.number('FPS', value=15, min=1, max=60, step=1).classes('w-28')

                def _select_detection(dets, target_id: Optional[int]):
                    if not dets:
                        return None
                    if target_id is not None:
                        cands = [d for d in dets if getattr(d, 'tag_id', None) == int(target_id)]
                        if cands:
                            return cands[0]
                        return None
                    # 选最近
                    def dist_of(d):
                        t = getattr(d, 'pose_t', None) or getattr(d, 'tvec', None)
                        if t is None:
                            return float('inf')
                        arr = np.asarray(t, float).reshape(-1)
                        return float(np.linalg.norm(arr)) if arr.size >= 3 else float('inf')
                    return min(dets, key=dist_of)

                def _tick():
                    # 1) 抓帧
                    raw_img = vs.read_frame(key=key)  # type: ignore
                    if raw_img is None:
                        img_widget.set_source(get_empty_img())
                        overlay_widget.set_source(get_empty_img())
                        detection_result_widget.set_content('检测结果：\n(无图像)')
                        pose_widget.set_content('定位结果：\n(无)')
                        if cam:
                            status_widget.set_content('摄像头状态：\n' + cam.get_status())
                        return

                    # 2) Tag36h11 检测
                    intrinsics = vs.get_camera_intrinsics(key)  # type: ignore
                    dets = vs.detect_tag36h11(raw_img, intrinsics)
                    overlay_img = Tag36h11Detector.draw_overlay(raw_img, dets)
                    det_text = Tag36h11Detector.get_result_text(dets)

                    # 3) 选一个 detection → 定位
                    target_id_val = tag_id_input.value
                    try:
                        target_id = int(target_id_val) if target_id_val is not None else None
                    except Exception:
                        target_id = None

                    det = _select_detection(dets, target_id)
                    pose = vs.locate_from_tag(det) if det is not None else None  # 核心调用

                    # 4) 显示
                    img_widget.set_source(prepare_image_for_display(raw_img))
                    overlay_widget.set_source(prepare_image_for_display(overlay_img))
                    detection_result_widget.set_content('检测结果：\n' + (det_text or ''))

                    if pose is not None:
                        pose_text = f"x={pose.x:.3f} m\ny={pose.y:.3f} m\nyaw={pose.yaw:.3f} rad ({_deg(pose.yaw):.1f}°)"
                    else:
                        pose_text = "(无有效定位)"
                    pose_widget.set_content('定位结果：\n' + pose_text)

                    if cam:
                        status_widget.set_content('摄像头状态：\n' + cam.get_status())

                def on_loop_toggle(enabled: bool):
                    # 切相机时外层已保证会取消旧 timer；这里只负责当前块
                    if enabled:
                        fps = int(debug_fps_input.value or 15)
                        timers['timer'] = ui.timer(1.0 / max(1, fps), _tick)
                        logger.info(f'[{key}] 定位测试循环启动：{fps} FPS')
                    else:
                        if timers['timer']:
                            timers['timer'].cancel()
                            timers['timer'] = None
                            logger.info(f'[{key}] 定位测试循环已停止')

                ui.checkbox('定位测试循环', value=False, on_change=lambda e: on_loop_toggle(bool(e.value)))

            # 画面与文本
            with ui.row().classes('q-gutter-sm'):
                with ui.column().classes('q-gutter-xs'):
                    ui.label('原图').classes('text-caption')
                    img_widget = ui.interactive_image(get_empty_img()).classes('rounded-borders')

                with ui.column().classes('q-gutter-xs'):
                    ui.label('Tag 叠加').classes('text-caption')
                    overlay_widget = ui.interactive_image(get_empty_img()).classes('rounded-borders')

                with ui.column().classes('q-gutter-xs'):
                    ui.label('状态 / 结果').classes('text-caption')
                    status_widget = ui.code((cam.get_status() if cam else '')).props('readonly dense').classes('w-64')
                    detection_result_widget = ui.code('').props('readonly dense').classes('w-64')
                    pose_widget = ui.code('').props('readonly dense').classes('w-64')
