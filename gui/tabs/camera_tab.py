from nicegui import ui
import numpy as np
from PIL import Image
from vision.camera import cameras


def np_to_pil(img_np):
    if img_np is None:
        return get_placeholder_img()
    if isinstance(img_np, Image.Image):
        return img_np
    return Image.fromarray(img_np.astype('uint8'), 'RGB')


def get_placeholder_img():
    return Image.open("assets/no_signal.png").convert("RGB")


def get_camera_imgs():
    results = []
    for cam in cameras:
        if cam.latest_frame is not None:
            img = cam.latest_frame
        else:
            img = np.array(get_placeholder_img())
        # 叠加AprilTag检测结果
        overlay = cam.extra_data.get('tag36h11_overlay', img)
        tag36h11_result = cam.extra_data.get('tag36h11_result_text', "无检测结果")
        res_str = f"分辨率: {cam.width}x{cam.height}" if getattr(
            cam, 'width', None) and getattr(cam, 'height', None) else "分辨率: -"
        fps_str = f"帧率: {cam.fps:.1f}" if getattr(
            cam, 'actual_fps', None) else "帧率: -"
        actual_fps_str = f"实际帧率: {cam.actual_fps:.1f}" if getattr(
            cam, 'actual_fps', None) else "实际帧率: -"
        text = f"{res_str}\n{fps_str}\n{actual_fps_str}\n{tag36h11_result}"
        results.append((img, overlay, text))
    return results


def render_camera_tab():

    ui.markdown('# 摄像头')
    with ui.row().classes('q-gutter-md q-mb-md'):
        ui.button('连接所有摄像头', color='primary', on_click=lambda: [
                  cam.connect() for cam in cameras])
        ui.button('断开所有摄像头', color='negative', on_click=lambda: [
                  cam.disconnect() for cam in cameras])
    cam_names = [cam.alias for cam in cameras]
    img_elems = []
    overlay_elems = []
    text_widgets = []
    with ui.column():
        for i, name in enumerate(cam_names):
            cam = cameras[i]
            with ui.card().classes('q-pa-md q-mb-md'):
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label(f"{name}").classes('text-h6')
                    # 右侧加入连接和断开按钮
                    connect_btn = ui.button('连接', color='primary')
                    disconnect_btn = ui.button('断开', color='negative')
                    def on_connect_click(cam=cam):
                        cam.connect()
                    def on_disconnect_click(cam=cam):
                        cam.disconnect()
                    connect_btn.on('click', lambda e, cam=cam: on_connect_click(cam))
                    disconnect_btn.on('click', lambda e, cam=cam: on_disconnect_click(cam))
                with ui.row().classes('q-gutter-md'):
                    img_id = f"cam_img_{i}"
                    img_elem = ui.html(
                        f'<img id="{img_id}" style="width:100%;max-width:320px;height:auto;object-fit:contain;background:#222;display:block;">')
                    img_elems.append(img_id)
                    overlay_id = f"cam_overlay_{i}"
                    overlay_elem = ui.html(
                        f'<img id="{overlay_id}" style="width:100%;max-width:320px;height:auto;object-fit:contain;background:#444;display:block;">')
                    overlay_elems.append(overlay_id)
                    text_widget = ui.textarea('').props('label=检测结果 readonly').classes(
                        'bg-grey-2 q-pa-sm').style('white-space:pre-line;word-break:break-all;min-width:200px;min-height:200px;')
                    text_widgets.append(text_widget)

    import io
    import base64

    def pil_to_base64(img):
        # 先缩放到最大宽度 320px，再压缩
        max_width = 480
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            resample = Image.Resampling.LANCZOS
            img = img.resize(new_size, resample)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=80)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    def update_imgs():
        results = get_camera_imgs()
        for i, (img, overlay, text) in enumerate(results):
            cam = cameras[i]
            
            # 原图
            pil_img = np_to_pil(img)
            b64 = pil_to_base64(pil_img)
            ui.run_javascript(
                f'document.getElementById("{img_elems[i]}").src = "data:image/jpeg;base64,{b64}";')
            
            # 叠加层
            pil_overlay = np_to_pil(overlay)
            b64_overlay = pil_to_base64(pil_overlay)
            ui.run_javascript(
                f'document.getElementById("{overlay_elems[i]}").src = "data:image/jpeg;base64,{b64_overlay}";')
            
            # 文本
            text_widgets[i].set_value(text)

    ui.timer(1.0/10, update_imgs)  # 30Hz刷新
