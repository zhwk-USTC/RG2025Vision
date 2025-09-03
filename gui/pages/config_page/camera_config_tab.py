from nicegui import ui
import numpy as np
from typing import Optional
from PIL import Image

from vision import get_vision, save_vision_config
from vision.camera_node.camera import get_camera_info_list
from vision.camera_node import CameraNode
from vision.detection.apriltag import TagDetectionConfig, TagDetectionConfig, Tag36h11Detector
from core.logger import logger


def _empty_image():
    return Image.fromarray(np.zeros((480, 640, 3), dtype=np.uint8))


def render_camera_config_tab():
    vs = get_vision()

    def on_save_config():
        save_vision_config()

    ui.button('保存配置', color='secondary', on_click=lambda e: on_save_config())

    # 默认：可独立展开多个
    for cam_node in vs._cam_nodes:
        render_camera_block(cam_node)


def render_camera_block(cam_node: CameraNode):
    cam_info_list = get_camera_info_list()
    cam_choices = {c.index: c.name for c in cam_info_list}

    # ---- 头部显示的可变状态 ----
    header_state = {'text': ''}

    def _header_text() -> str:
        alias = cam_node.alias or '未命名'
        name = cam_node.camera_name or '未选择'
        idx = cam_node.camera_index if cam_node.camera_index is not None else '-'
        return f'{alias} · {name} · index={idx}'

    def _refresh_header():
        header_state['text'] = _header_text()

    # ---- 事件处理 ----
    def on_camera_change(index: int):
        cam_node.select_camera_by_index(index)
        logger.info(
            f'{cam_node.alias} 已选择摄像头 {cam_node.camera_name} (index={index})')
        _refresh_header()

    def on_alias_change(value: str):
        cam_node.alias = value
        logger.info(f'摄像头 {cam_node.camera_name} 的别名已更改为 {value}')
        _refresh_header()

    def on_width_change(value: int):
        cam_node.set_width(value)
        logger.info(f'摄像头 {cam_node.alias} 的宽度已更改为 {value}')

    def on_height_change(value: int):
        cam_node.set_height(value)
        logger.info(f'摄像头 {cam_node.alias} 的高度已更改为 {value}')

    def on_fps_change(value: int):
        cam_node.set_camera_fps(value)
        logger.info(f'摄像头 {cam_node.alias} 的帧率已更改为 {value}')

    def on_connect_camera():
        cam_node.start()
        logger.info(f'摄像头 {cam_node.alias} 已连接')
        _refresh_header()

    def on_disconnect_camera():
        cam_node.stop()
        logger.info(f'摄像头 {cam_node.alias} 已断开连接')
        _refresh_header()

    async def on_refresh_image():
        try:
            frame = await cam_node.read_frame_async()
            if frame is not None:
                img_widget.set_source(Image.fromarray(frame))
                logger.info(f'摄像头 {cam_node.alias} 图像已刷新')
            else:
                img_widget.set_source(_empty_image())
                logger.warning(f'摄像头 {cam_node.alias} 图像为空图像')

            status_widget.set_content(cam_node.status)
        except Exception as e:
            logger.error(f'摄像头 {cam_node.alias} 图像刷新失败: {e}')

    # ---- 可展开的元素 ----
    _refresh_header()
    with ui.expansion(value=False).classes('w-full q-mb-md') as exp:
        # 自定义 header（图标 + 动态标题）
        with exp.add_slot('header'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('videocam')
                ui.label().bind_text_from(header_state, 'text')

        # 展开后的内容
        with ui.card().classes('q-pa-md w-full'):
            with ui.row().classes('q-gutter-xl'):
                # 左侧：参数与操作
                with ui.column():
                    ui.select(
                        cam_choices,
                        value=cam_node.camera_index,
                        label='选择摄像头',
                        on_change=lambda e: on_camera_change(e.value),
                    )
                    ui.input(
                        label='别名',
                        value=cam_node.alias,
                        on_change=lambda e: on_alias_change(e.value),
                    )
                    ui.number(
                        label='宽度',
                        value=cam_node.width,
                        format='%.0f',
                        on_change=lambda e: on_width_change(
                            int(e.value)) if e.value else None,
                    )
                    ui.number(
                        label='高度',
                        value=cam_node.height,
                        format='%.0f',
                        on_change=lambda e: on_height_change(
                            int(e.value)) if e.value else None,
                    )
                    ui.number(
                        label='帧率',
                        value=cam_node.camera_fps,
                        format='%.0f',
                        on_change=lambda e: on_fps_change(
                            int(e.value)) if e.value else None,
                    )
                    with ui.row():
                        ui.button('连接', color='primary',
                                  on_click=lambda e: on_connect_camera())
                        ui.button('断开连接', color='negative',
                                  on_click=lambda e: on_disconnect_camera())

                # 中间：图像与刷新
                with ui.column().classes('q-gutter-sm'):
                    img_widget = ui.interactive_image(_empty_image())
                    ui.button('刷新图像', icon='refresh',
                              on_click=lambda e: on_refresh_image())

                # 右侧：信息
                with ui.column().classes('q-gutter-sm'):
                    status_widget = ui.code(cam_node.status).props('readonly')

        with ui.card().classes('q-pa-md q-mb-md'):
            tag36h11_config = cam_node._tag36h11_detector.get_config(
            ) if cam_node._tag36h11_detector else None
            if not tag36h11_config:
                logger.warning(f'{cam_node.alias} 的 AprilTag36h11 检测器未配置,使用默认配置')
                tag36h11_config = TagDetectionConfig()
                tag36h11_config.families = 'tag36h11'

            def on_quad_decimate(value):
                tag36h11_config.quad_decimate = float(
                    value) if value is not None else 2.0
                quad_decimate_value.text = f"{value}"

            def on_quad_sigma(value):
                tag36h11_config.quad_sigma = float(
                    value) if value is not None else 0.0
                quad_sigma_value.text = f"{value}"

            def on_decode_sharpening(value):
                tag36h11_config.decode_sharpening = float(
                    value) if value is not None else 0.25
                decode_sharpening_value.text = f"{value}"

            def on_nthreads(value):
                if value is not None:
                    tag36h11_config.nthreads = int(value)
                    nthreads_value.text = f"{value}"

            def on_refine_edges(value):
                if value is not None:
                    checked = bool(int(value))
                    tag36h11_config.refine_edges = checked
                    refine_edges_value.text = f"{int(checked)}"
            
            def on_use_tag36h11(value):
                if value:
                    cam_node.enable_tag36h11 = True
                    logger.info(f'{cam_node.alias} 的 AprilTag36h11 检测器已创建')
                    tag36h11_config_box.set_visibility(True)
                else:
                    cam_node.enable_tag36h11 = False
                    logger.info(f'{cam_node.alias} 的 AprilTag36h11 检测器已删除')
                    tag36h11_config_box.set_visibility(False)

            def on_apply_tag36h11():
                if( not cam_node._tag36h11_detector):
                    cam_node._tag36h11_detector = Tag36h11Detector(tag36h11_config)
                    logger.info(f'{cam_node.alias} 的 AprilTag36h11 检测器已创建')
                else:
                    cam_node._tag36h11_detector.update_config(tag36h11_config)
                    logger.info(f'{cam_node.alias} 的 AprilTag36h11 检测器配置已更新')
                logger.info('AprilTag配置已应用')

            ui.checkbox('启用 Tag36h11 检测器', value=cam_node.enable_tag36h11, on_change=lambda e: on_use_tag36h11(e.value))
            tag36h11_config_box = ui.card()
            if cam_node.enable_tag36h11:
                tag36h11_config_box.set_visibility(True)
            else:
                tag36h11_config_box.set_visibility(False)
            with tag36h11_config_box:
                ui.label('tag36h11参数').classes('text-h6')
                # 每行一个参数，label-滑条-数值，并加中文注释说明作用
                with ui.column().classes('q-gutter-xs'):
                    with ui.row().classes('items-center q-gutter-md'):
                        # quad_decimate：图像下采样倍数，越大速度越快但精度下降，推荐1.0~2.0
                        ui.label('quad_decimate').style('min-width:110px')
                        quad_decimate_input = ui.slider(
                            value=tag36h11_config.quad_decimate, min=1.0, max=4.0, step=0.1,
                            on_change=lambda e: on_quad_decimate(e.value)).style(
                            'min-width:240px;max-width:400px;flex:1')
                        quad_decimate_value = ui.label(f"{tag36h11_config.quad_decimate}").style(
                            'min-width:48px;text-align:right')
                        ui.label('图像下采样倍数，越大速度越快但精度下降').style(
                            'color:#888;font-size:13px')
                    with ui.row().classes('items-center q-gutter-md'):
                        # quad_sigma：高斯模糊参数，抑制噪声，0为不模糊
                        ui.label('quad_sigma').style('min-width:110px')
                        quad_sigma_input = ui.slider(
                            value=tag36h11_config.quad_sigma, min=0.0, max=2.0, step=0.1,
                            on_change=lambda e: on_quad_sigma(e.value)).style(
                            'min-width:240px;max-width:400px;flex:1')
                        quad_sigma_value = ui.label(f"{tag36h11_config.quad_sigma}").style(
                            'min-width:48px;text-align:right')
                        ui.label('高斯模糊参数，抑制噪声，0为不模糊').style(
                            'color:#888;font-size:13px')
                    with ui.row().classes('items-center q-gutter-md'):
                        # decode_sharpening：解码锐化参数，提升边缘清晰度
                        ui.label('decode_sharpening').style('min-width:110px')
                        decode_sharpening_input = ui.slider(
                            value=tag36h11_config.decode_sharpening, min=0.0, max=1.0, step=0.1,
                            on_change=lambda e: on_decode_sharpening(e.value)
                            ).style(
                            'min-width:240px;max-width:400px;flex:1')
                        decode_sharpening_value = ui.label(f"{tag36h11_config.decode_sharpening}").style(
                            'min-width:48px;text-align:right')
                        ui.label('解码锐化参数，提升边缘清晰度').style(
                            'color:#888;font-size:13px')
                    with ui.row().classes('items-center q-gutter-md'):
                        # nthreads：线程数，提升检测速度，推荐与CPU核心数一致
                        ui.label('nthreads').style('min-width:110px')
                        nthreads_input = ui.slider(
                            value=tag36h11_config.nthreads, min=1, max=16, step=1,
                            on_change=lambda e:on_nthreads(e.value)).style(
                            'min-width:240px;max-width:400px;flex:1')
                        nthreads_value = ui.label(f"{tag36h11_config.nthreads}").style(
                            'min-width:48px;text-align:right')
                        ui.label('线程数，提升检测速度，推荐与CPU核心数一致').style(
                            'color:#888;font-size:13px')
                    with ui.row().classes('items-center q-gutter-md'):
                        # refine_edges：是否优化边缘检测，提升精度但略慢
                        ui.label('refine_edges').style('min-width:110px')
                        refine_edges_input = ui.slider(value=int(bool(tag36h11_config.refine_edges)), min=0, max=1, step=1).style(
                            'min-width:240px;max-width:400px;flex:1')
                        refine_edges_value = ui.label(f"{int(bool(tag36h11_config.refine_edges))}").style(
                            'min-width:48px;text-align:right')
                        ui.label('是否优化边缘检测，提升精度但略慢').style('color:#888;font-size:13px')

                ui.button('应用配置', on_click=on_apply_tag36h11, color='primary')