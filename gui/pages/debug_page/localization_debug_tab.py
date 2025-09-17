from typing import Optional, Union
import numpy as np
from PIL import Image
from nicegui import ui
from core.logger import logger
from vision import get_vision
from vision.detection import Tag36h11Detector, Tag25h9Detector

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
    return Image.new("RGB", (320, 240), (200, 200, 200))

def get_tag_debug_img(tag_family: str):
    try:
        if tag_family == 'tag36h11':
            img = Image.open("assets\\apriltag-imgs\\tag36h11\\tag36_11_00000.png")
        elif tag_family == 'tag25h9':
            img = Image.open("assets\\apriltag-imgs\\tag25h9\\tag25_09_00000.png")
        else:
            return get_empty_img()
        return img.resize((300, 300), Image.Resampling.NEAREST)
    except Exception as e:
        logger.warning(f"无法加载调试图片 {tag_family}: {e}")
        return get_empty_img()

def get_rotated_tag_img(tag_family: str, tag_id: int = 1, rotation_degrees: int = 90):
    """获取旋转的tag图像"""
    try:
        if tag_family == 'tag36h11':
            # 尝试加载指定ID的tag图像
            img_path = f"assets\\apriltag-imgs\\tag36h11\\tag36_11_{tag_id:05d}.png"
            try:
                img = Image.open(img_path)
            except FileNotFoundError:
                # 如果指定ID不存在，使用默认的tag
                img = Image.open("assets\\apriltag-imgs\\tag36h11\\tag36_11_00000.png")
                logger.warning(f"Tag ID {tag_id} 不存在，使用默认tag")
        elif tag_family == 'tag25h9':
            # 尝试加载指定ID的tag图像
            img_path = f"assets\\apriltag-imgs\\tag25h9\\tag25_09_{tag_id:05d}.png"
            try:
                img = Image.open(img_path)
            except FileNotFoundError:
                # 如果指定ID不存在，使用默认的tag
                img = Image.open("assets\\apriltag-imgs\\tag25h9\\tag25_09_00000.png")
                logger.warning(f"Tag ID {tag_id} 不存在，使用默认tag")
        else:
            return get_empty_img()
        
        # 旋转图像
        rotated_img = img.rotate(rotation_degrees, expand=True)
        return rotated_img.resize((300, 300), Image.Resampling.NEAREST)
    except Exception as e:
        logger.warning(f"无法加载旋转tag图片 {tag_family} ID:{tag_id}: {e}")
        return get_empty_img()

def get_tag36h11_debug_img():
    return get_tag_debug_img('tag36h11')

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
    
    # 全局状态用于存储 tag family 和相关配置
    global_state = {
        'tag_family': 'tag36h11',
        'tag_size': 0.1,  # 默认 tag size 10cm
    }
    
    with ui.row().classes('q-gutter-xl'):
        with ui.column().classes('items-start'):
            with ui.row().classes('items-center gap-2'):
                ui.label('Tag Family').classes('text-caption')
                tag_family_select = ui.select(
                    options={'tag36h11': 'Tag36h11', 'tag25h9': 'Tag25h9'},
                    value=global_state['tag_family'],
                    on_change=lambda e: _on_tag_family_change(e.value, global_state, tag_example_widget, rotated_tag_widget),
                ).classes('w-32')
                
                ui.label('Tag Size').classes('text-caption')
                tag_size_input = ui.number('', value=global_state['tag_size'], min=0.001, max=10.0, step=0.001, format='%.3f').classes('w-32')
                tag_size_input.on('update:model-value', lambda e: _on_tag_size_change(e.args, global_state))
                ui.label('米').classes('text-caption')
            
            with ui.row().classes('q-gutter-md'):
                with ui.column().classes('items-center'):
                    ui.label('标准 Tag').classes('text-subtitle2')
                    tag_example_widget = ui.interactive_image(get_tag_debug_img(global_state['tag_family']))
                
                with ui.column().classes('items-center'):
                    ui.label('ID=1 旋转90°').classes('text-subtitle2')
                    rotated_tag_widget = ui.interactive_image(get_rotated_tag_img(global_state['tag_family'], 1, 90))
            
        with ui.column().classes('items-start'):
            ui.label('坐标系方向').classes('text-subtitle2')
            with ui.card().classes('p-4'):
                ui.label('X轴: 右 →').classes('text-sm')
                ui.label('Y轴: 下 ↓').classes('text-sm')
                ui.label('Z轴: 内 ⦿').classes('text-sm')
                ui.label('(右手坐标系)').classes('text-xs text-gray-500')
    
    def _on_tag_family_change(new_family: str, state: dict, example_widget, rotated_widget):
        state['tag_family'] = new_family
        example_widget.set_source(get_tag_debug_img(new_family))
        rotated_widget.set_source(get_rotated_tag_img(new_family, 1, 90))
        logger.info(f'切换到 tag family: {new_family}')
    
    def _on_tag_size_change(new_size, state: dict):
        try:
            state['tag_size'] = float(new_size)
            logger.info(f'设置 tag size: {new_size}m')
        except (TypeError, ValueError):
            logger.warning(f'无效的 tag size 值: {new_size}')
    
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
            render_localization_block(new_key, timers, global_state, parent=block_container)

    # 初次渲染
    _on_cam_change(state['cam_key'])


# ---------------------------
# 单相机定位测试块
# ---------------------------
def render_localization_block(key: str, timers: dict, global_state: dict, parent=None):
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
                debug_fps_input = ui.number('FPS', value=5, min=1, max=60, step=1).classes('w-28')

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
                        t = getattr(d, 'pose_t', None)
                        if t is None:
                            t = getattr(d, 'tvec', None)
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

                    # 2) 根据选择的 tag family 进行检测
                    intrinsics = vs.get_camera_intrinsics(key)  # type: ignore
                    tag_family = global_state.get('tag_family', 'tag36h11')
                    tag_size = global_state.get('tag_size', 0.1)
                    
                    if tag_family == 'tag36h11':
                        dets = vs.detect_tag36h11(raw_img, intrinsics, tag_size=tag_size)
                        overlay_img = Tag36h11Detector.draw_overlay(raw_img, dets)
                        det_text = Tag36h11Detector.get_result_text(dets)
                    elif tag_family == 'tag25h9':
                        dets = vs.detect_tag25h9(raw_img, intrinsics, tag_size=tag_size)
                        overlay_img = Tag25h9Detector.draw_overlay(raw_img, dets)
                        det_text = Tag25h9Detector.get_result_text(dets)
                    else:
                        dets = None
                        overlay_img = raw_img
                        det_text = f"不支持的 tag family: {tag_family}"

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
                        pose_text = (
                            f"x={pose.x:.3f} m\n"
                            f"y={pose.y:.3f} m\n"
                            f"z={pose.z:.3f} m\n"
                            f"roll={pose.roll:.3f} rad ({_deg(pose.roll):.1f}°)\n"
                            f"pitch={pose.pitch:.3f} rad ({_deg(pose.pitch):.1f}°)\n"
                            f"yaw={pose.yaw:.3f} rad ({_deg(pose.yaw):.1f}°)"
                        )
                    else:
                        pose_text = "(无有效定位)"
                    pose_widget.set_content('定位结果：\n' + pose_text)

                    if cam:
                        status_widget.set_content('摄像头状态：\n' + cam.get_status())

                def on_loop_toggle(enabled: bool):
                    # 切相机时外层已保证会取消旧 timer；这里只负责当前块
                    if enabled:
                        fps = int(debug_fps_input.value or 5)
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

                with ui.column().classes('q-gutter-xs'):
                    ui.label('摄像头内参').classes('text-caption')
                    intrinsics = vs.get_camera_intrinsics(key) # type: ignore
                    if intrinsics:
                        intrin_text = f"fx={getattr(intrinsics, 'fx', None)}\nfy={getattr(intrinsics, 'fy', None)}\ncx={getattr(intrinsics, 'cx', None)}\ncy={getattr(intrinsics, 'cy', None)}"
                    else:
                        intrin_text = "(无内参信息)"
                    ui.code(intrin_text).props('readonly dense').classes('w-64')
