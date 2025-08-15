from nicegui import ui
import numpy as np
from PIL import Image

from vision.camera import cameras
from core.logger import logger


def np_to_pil(img_np):
    if img_np is None:
        return get_placeholder_img()
    if isinstance(img_np, Image.Image):
        return img_np
    return Image.fromarray(img_np.astype('uint8'), 'RGB')


def get_placeholder_img():
    return Image.open("assets/no_signal.png").convert("RGB")


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
        camera_info = f"{res_str}\n{fps_str}\n{actual_fps_str}"
        
        # 检测结果
        detection_result = tag36h11_result
        
        results.append((img, overlay, camera_info, detection_result))
    return results


def render_camera_tab():

    ui.markdown('# 摄像头')
    with ui.row().classes('q-gutter-md q-mb-md'):
        ui.button('连接所有摄像头', color='primary', on_click=lambda: [
                  cam.connect() for cam in cameras])
        ui.button('断开所有摄像头', color='negative', on_click=lambda: [
                  cam.disconnect() for cam in cameras])
        
    cam_names = [cam.alias for cam in cameras]
    img_widgets = []
    overlay_widgets = []
    camera_info_widgets = []
    detection_result_widgets = []
    
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
                
                placeholder_img = prepare_image_for_display(np.array(get_placeholder_img()))
                
                with ui.row().classes('q-gutter-sm'):
                    with ui.column().classes('q-gutter-sm'):
                        ui.label('原图').classes('text-subtitle2')
                        img_widget = ui.interactive_image(
                            placeholder_img
                        ).classes('max-w-80').style('max-width: 320px; height: auto;')
                        img_widgets.append(img_widget)
                    
                    with ui.column().classes('q-gutter-sm'):
                        ui.label('检测叠加').classes('text-subtitle2')
                        overlay_widget = ui.interactive_image(
                            placeholder_img
                        ).classes('max-w-80').style('max-width: 320px; height: auto;')
                        overlay_widgets.append(overlay_widget)
                    
                    
                    camera_info_widget = ui.textarea('').props('label=摄像头信息 readonly').classes(
                        'bg-blue-1 q-pa-sm').style('white-space:pre-line;word-break:break-all;min-width:150px;min-height:200px;flex:1;')
                    camera_info_widgets.append(camera_info_widget)
                    
                    detection_result_widget = ui.textarea('').props('label=检测结果 readonly').classes(
                        'bg-green-1 q-pa-sm').style('white-space:pre-line;word-break:break-all;min-width:300px;min-height:200px;flex:1;')
                    detection_result_widgets.append(detection_result_widget)

    
    def update_imgs():
        results = get_camera_imgs()
        for i, (img, overlay, camera_info, detection_result) in enumerate(results):
            cam = cameras[i]
            
            # 原图
            processed_img = prepare_image_for_display(img)
            img_widgets[i].set_source(processed_img)
            
            # 叠加层
            processed_overlay = prepare_image_for_display(overlay)
            overlay_widgets[i].set_source(processed_overlay)
            
            # 摄像头信息
            camera_info_widgets[i].set_value(camera_info)
            # 检测结果
            detection_result_widgets[i].set_value(detection_result)

    ui.timer(1.0/5, update_imgs)  # 30Hz刷新
