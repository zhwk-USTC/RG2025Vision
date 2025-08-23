from nicegui import ui
from vision.camera import cameras, camera_info_list, setup_camera_info
from vision.config import save_camera_config, load_camera_config
from vision.apriltag import save_config as save_apriltag_config, apply_config as apply_apriltag_config

from PIL import Image
import numpy as np
from core.logger import logger

def get_placeholder_img():
    return Image.open("assets/no_signal.png").convert("RGB")


def render_apriltag_config():
    ui.markdown('## AprilTag检测参数')
    from vision.apriltag import TAG36H11_CONFIG
    apriltag_config = TAG36H11_CONFIG
    with ui.card().classes('q-pa-md q-mb-md'):
        ui.label('tag36h11参数').classes('text-h6')
        # 每行一个参数，label-滑条-数值，并加中文注释说明作用
        with ui.column().classes('q-gutter-xs'):
            with ui.row().classes('items-center q-gutter-md'):
                # quad_decimate：图像下采样倍数，越大速度越快但精度下降，推荐1.0~2.0
                ui.label('quad_decimate').style('min-width:110px')
                quad_decimate_input = ui.slider(value=apriltag_config['quad_decimate'], min=1.0, max=4.0, step=0.1).style('min-width:240px;max-width:400px;flex:1')
                quad_decimate_value = ui.label(f"{apriltag_config['quad_decimate']}").style('min-width:48px;text-align:right')
                ui.label('图像下采样倍数，越大速度越快但精度下降').style('color:#888;font-size:13px')
            with ui.row().classes('items-center q-gutter-md'):
                # quad_sigma：高斯模糊参数，抑制噪声，0为不模糊
                ui.label('quad_sigma').style('min-width:110px')
                quad_sigma_input = ui.slider(value=apriltag_config['quad_sigma'], min=0.0, max=2.0, step=0.1).style('min-width:240px;max-width:400px;flex:1')
                quad_sigma_value = ui.label(f"{apriltag_config['quad_sigma']}").style('min-width:48px;text-align:right')
                ui.label('高斯模糊参数，抑制噪声，0为不模糊').style('color:#888;font-size:13px')
            with ui.row().classes('items-center q-gutter-md'):
                # decode_sharpening：解码锐化参数，提升边缘清晰度
                ui.label('decode_sharpening').style('min-width:110px')
                decode_sharpening_input = ui.slider(value=apriltag_config['decode_sharpening'], min=0.0, max=1.0, step=0.1).style('min-width:240px;max-width:400px;flex:1')
                decode_sharpening_value = ui.label(f"{apriltag_config['decode_sharpening']}").style('min-width:48px;text-align:right')
                ui.label('解码锐化参数，提升边缘清晰度').style('color:#888;font-size:13px')
            with ui.row().classes('items-center q-gutter-md'):
                # nthreads：线程数，提升检测速度，推荐与CPU核心数一致
                ui.label('nthreads').style('min-width:110px')
                nthreads_input = ui.slider(value=apriltag_config['nthreads'], min=1, max=16, step=1).style('min-width:240px;max-width:400px;flex:1')
                nthreads_value = ui.label(f"{apriltag_config['nthreads']}").style('min-width:48px;text-align:right')
                ui.label('线程数，提升检测速度，推荐与CPU核心数一致').style('color:#888;font-size:13px')
        with ui.row().classes('items-center q-gutter-md'):
            # refine_edges：是否优化边缘检测，提升精度但略慢
            ui.label('refine_edges').style('min-width:110px')
            refine_edges_input = ui.slider(value=int(bool(apriltag_config['refine_edges'])), min=0, max=1, step=1).style('min-width:240px;max-width:400px;flex:1')
            refine_edges_value = ui.label(f"{int(bool(apriltag_config['refine_edges']))}").style('min-width:48px;text-align:right')
            ui.label('是否优化边缘检测，提升精度但略慢').style('color:#888;font-size:13px')
        def on_quad_decimate(e):
            value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
            apriltag_config['quad_decimate'] = value
            quad_decimate_value.text = f"{value}"
        quad_decimate_input.on('update:model-value', on_quad_decimate)
        def on_quad_sigma(e):
            value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
            apriltag_config['quad_sigma'] = value
            quad_sigma_value.text = f"{value}"
        quad_sigma_input.on('update:model-value', on_quad_sigma)
        def on_decode_sharpening(e):
            value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
            apriltag_config['decode_sharpening'] = value
            decode_sharpening_value.text = f"{value}"
        decode_sharpening_input.on('update:model-value', on_decode_sharpening)
        def on_nthreads(e):
            value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
            if value is not None:
                try:
                    apriltag_config['nthreads'] = int(value)
                    nthreads_value.text = f"{value}"
                except Exception as ex:
                    logger.error(f"nthreads转换失败: {ex}")
        nthreads_input.on('update:model-value', on_nthreads)
        def on_refine_edges(e):
            value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
            if value is not None:
                try:
                    checked = bool(int(value))
                except Exception as ex:
                    logger.error(f"refine_edges转换失败: {ex}")
                    checked = False
                apriltag_config['refine_edges'] = checked
                refine_edges_value.text = f"{int(checked)}"
        refine_edges_input.on('update:model-value', on_refine_edges)

        with ui.row().classes('q-mt-md q-gutter-md'):
            def on_apply_apriltag_click():
                apply_apriltag_config()
                logger.info('AprilTag配置已应用')
            ui.button('应用配置', on_click=on_apply_apriltag_click, color='primary')
            def on_save_apriltag_click():
                save_apriltag_config()
                logger.info('AprilTag配置已保存')
            ui.button('保存配置', on_click=on_save_apriltag_click, color='secondary')


def render_camera_config():

    def get_info_text(cam):
        info_lines = [
            f"别名: {cam.alias}",
            f"索引: {getattr(cam.info, 'index', '')}",
            f"名称: {getattr(cam.info, 'name', '')}",
            f"分辨率: {cam.width}x{cam.height}",
            f"帧率: {cam.fps}",
            f"连接状态: {'已连接' if getattr(cam, 'connected', False) else '未连接'}"
        ]
        return '\n'.join(info_lines)

    cam_choices = [(c.name, i) for i, c in enumerate(camera_info_list)]
    res_choices = ["请选择", "640x480", "800x600", "1280x720", "1920x1080"]
    fps_choices = ["15", "30", "60"]

    ui.markdown('## 摄像头配置')
            
    def on_rescan_cameras():
        """重新检测摄像头"""
        logger.info("正在重新检测摄像头...")
        try:
            setup_camera_info()
            nonlocal cam_choices; 
            cam_choices = [(c.name, i) for i, c in enumerate(camera_info_list)]
            load_camera_config()
            logger.info("摄像头重新检测完成")
        except Exception as e:
            logger.error(f"摄像头检测失败: {str(e)}")
            
    # TODO: 待实现刷新摄像头列表功能
    # ui.button('重新检测摄像头', color='accent', icon='refresh', on_click=on_rescan_cameras)

    for idx, cam in enumerate(cameras):
        name = cam.alias if cam.alias else f"摄像头{idx}"
        def render_cam_block(cam=cam, idx=idx):
            with ui.card().classes('q-pa-md q-mb-md'):
                ui.label(f"{name}").classes('text-h6')
                with ui.row().classes('q-gutter-xl'):
                    # 左侧参数与操作
                    with ui.column().classes('q-gutter-sm'):
                        idx_dropdown = ui.select([c[0] for c in cam_choices], value=cam.info.name if cam.info else None, label='选择摄像头').classes('w-full')
                        alias_box = ui.input(label='别名', value=cam.alias or '').classes('w-full')
                        res_dropdown = ui.select(res_choices, value=f"{cam.width}x{cam.height}" if cam.width and cam.height else res_choices[0], label='分辨率').classes('w-full')
                        fps_dropdown = ui.select(fps_choices, value=str(int(cam.fps)) if cam.fps else fps_choices[0], label='帧率').classes('w-full')
                        tag36h11_checkbox = ui.checkbox('tag36h11', value=getattr(cam, 'tag36h11_enabled', False)).classes('w-full')
                        def on_tag36h11_enabled_change(e, cam=cam):
                            value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
                            # 兼容NiceGUI事件参数为bool或[bool, event]
                            if isinstance(value, list):
                                checked = bool(value[0])
                            else:
                                checked = bool(value)
                            logger.info(f"{cam.alias} tag36h11状态修改: {checked}")
                            cam.tag36h11_enabled = checked
                            logger.info(f"已设置 {cam.alias} tag36h11_enabled={cam.tag36h11_enabled}")
                        tag36h11_checkbox.on('update:model-value', on_tag36h11_enabled_change)
                        with ui.row().classes('q-gutter-sm'):
                            save_btn = ui.button('保存配置', color='secondary')
                            connect_btn = ui.button('连接', color='primary')
                            disconnect_btn = ui.button('断开连接', color='negative')
                    # 右侧图像与信息
                    with ui.column().classes('q-gutter-sm'):
                        img_widget = ui.interactive_image(get_placeholder_img()).style('width:320px;height:auto;object-fit:contain;display:block;').classes('shadow-2')
                        refresh_btn = ui.button('刷新图像', icon='refresh')
                    with ui.column().classes('q-gutter-sm'):
                        info_label = ui.textarea(get_info_text(cam)).props('label=摄像头信息 readonly rows=10').classes('bg-grey-2 q-pa-sm').style('white-space:pre-line;word-break:break-all;min-width:320px;min-height:200px;')


                def on_idx_change(e, cam=cam):
                    value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
                    # 兼容NiceGUI返回dict或int
                    idx = None
                    if isinstance(value, dict) and 'value' in value:
                        idx = value['value']
                    elif isinstance(value, int):
                        idx = value
                    elif isinstance(value, str) and value.isdigit():
                        idx = int(value)
                    logger.debug(f"{cam.alias}序号选择: {value} (idx={idx})")
                    if idx is not None:
                        cam.select_camera(idx)
                idx_dropdown.on('update:model-value', on_idx_change)

                def on_alias_change(e, cam=cam):
                    value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
                    logger.debug(f"{cam.alias}别名修改: {value}")
                    cam.alias = value
                alias_box.on('update:model-value', on_alias_change)

                def on_res_change(e, cam=cam):
                    value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
                    # 兼容NiceGUI返回dict、str
                    res_str = None
                    if isinstance(value, dict) and 'label' in value:
                        res_str = value['label']
                    elif isinstance(value, dict) and 'value' in value:
                        res_str = value['value']
                    elif isinstance(value, str):
                        res_str = value
                    logger.debug(f"{cam.alias}分辨率选择: {value} (res_str={res_str})")
                    if res_str and 'x' in res_str:
                        width, height = res_str.split('x')
                        cam.width, cam.height = int(width), int(height)
                        logger.debug(f"已写入cam.width={cam.width}, cam.height={cam.height}")
                res_dropdown.on('update:model-value', on_res_change)

                def on_fps_change(e, cam=cam):
                    value = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
                    # 兼容NiceGUI返回dict、str、int
                    fps_val = None
                    if isinstance(value, dict) and 'label' in value:
                        fps_val = value['label']
                    elif isinstance(value, dict) and 'value' in value:
                        fps_val = value['value']
                    elif isinstance(value, (str, int)):
                        fps_val = value
                    logger.debug(f"{cam.alias}帧率选择: {value} (fps_val={fps_val})")
                    if fps_val is not None:
                        try:
                            cam.fps = int(fps_val)
                        except Exception as ex:
                            logger.error(f"帧率转换失败: {ex}")
                fps_dropdown.on('update:model-value', on_fps_change)

                def on_save_click(cam=cam):
                    save_camera_config()
                save_btn.on('click', lambda e, cam=cam: on_save_click(cam))

                def on_connect_click(cam=cam):
                    cam.connect()
                    info_label.set_value(get_info_text(cam))
                connect_btn.on('click', lambda e, cam=cam: on_connect_click(cam))

                def on_disconnect_click(cam=cam):
                    cam.disconnect()
                    info_label.set_value(get_info_text(cam))
                disconnect_btn.on('click', lambda e, cam=cam: on_disconnect_click(cam))

                def update_img():
                    info_label.set_value(get_info_text(cam))
                    try:
                        if cam.connected:
                            frame = cam.latest_frame
                        else:
                            frame = None
                    except Exception as ex:
                        logger.error(f"刷新图像失败: {ex}")
                        frame = None
                    img = frame if frame is not None else np.array(get_placeholder_img())
                    img_widget.set_source(Image.fromarray(img.astype('uint8'), 'RGB'))
                    info_label.set_value(get_info_text(cam))

                refresh_btn.on('click', update_img)

        render_cam_block()

def render_config_tab():
    with ui.row().classes('items-center q-gutter-md'):
        ui.markdown('# 配置')

    render_apriltag_config()
    render_camera_config()
