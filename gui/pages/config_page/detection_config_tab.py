from nicegui import ui
import numpy as np
from typing import Optional
from PIL import Image

from vision import get_vision, save_vision_config
from vision.detection.apriltag import TagDetectionConfig, Tag36h11Detector
from vision.detection.hsv import HSVDetector, HSVDetectConfig
from core.logger import logger


def _empty_image():
    return Image.fromarray(np.zeros((480, 640, 3), dtype=np.uint8))


def render_detection_config_tab():
    vs = get_vision()

    def on_save_config():
        save_vision_config()
        
    with ui.row():
        ui.button('保存配置', color='secondary', on_click=lambda e: on_save_config())
    render_tag36h11_configs()
    render_hsv_configs()
    
def render_tag36h11_configs():
    with ui.card():
        ui.label('Tag36h11 检测器配置').classes('text-h5')
        vs = get_vision()
        def on_add_tag36h11_detector():
            new_detector_name = new_detector_name_input.value
            if not new_detector_name:
                logger.warning("未输入 tag36h11 检测器名称")
                return
            vs.add_tag36h11_detector(new_detector_name)

        with ui.row():
            new_detector_name_input = ui.input(label='添加 tag36h11 检测器', placeholder='输入摄像头别名')
            ui.button('添加 tag36h11 检测器', color='primary', on_click=lambda e: on_add_tag36h11_detector())

        for key, detector in vs._apriltag_36h11_detectors.items():
            render_tag36h11_block(key, detector)

def render_tag36h11_block(key: str, detector: Tag36h11Detector):
    # ---- 头部显示的可变状态 ----
    header_state = {'text': ''}

    def _header_text() -> str:
        alias = key or '未命名'
        name = 'tag36h11'
        return f'{alias} · {name}'

    def _refresh_header():
        header_state['text'] = _header_text()

    # ---- 事件处理 ----
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

    def on_apply_tag36h11():
        detector.update_config(tag36h11_config)
        logger.info(f'{key} 的 AprilTag36h11 检测器配置已更新')

    # ---- 可展开的元素 ----
    _refresh_header()
    with ui.expansion(value=False).classes('w-full q-mb-md') as exp:
        # 自定义 header（图标 + 动态标题）
        with exp.add_slot('header'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('qr_code')
                ui.label().bind_text_from(header_state, 'text')
        tag36h11_config = detector.get_config()
        with ui.card():
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
                    refine_edges_input = ui.slider(value=int(bool(tag36h11_config.refine_edges)), min=0, max=1, step=1
                                                   ,on_change=lambda e:on_refine_edges(e.value)).style(
                        'min-width:240px;max-width:400px;flex:1')
                    refine_edges_value = ui.label(f"{int(bool(tag36h11_config.refine_edges))}").style(
                        'min-width:48px;text-align:right')
                    ui.label('是否优化边缘检测，提升精度但略慢').style('color:#888;font-size:13px')

            ui.button('应用配置', on_click=on_apply_tag36h11, color='primary')
            
def render_hsv_configs():
    with ui.card():
        ui.label('HSV 检测器配置').classes('text-h5')
        vs = get_vision()

        def on_add_hsv_detector():
            new_name = new_detector_name_input.value
            if not new_name:
                logger.warning("未输入 HSV 检测器名称")
                return
            vs.add_hsv_detector(new_name)
            logger.info(f"已添加 HSV 检测器: {new_name}")

        with ui.row():
            new_detector_name_input = ui.input(label='添加 HSV 检测器', placeholder='输入摄像头别名')
            ui.button('添加 HSV 检测器', color='primary', on_click=lambda e: on_add_hsv_detector())

        # 遍历已存在的 HSV 检测器
        for key, detector in get_vision()._hsv_detectors.items():
            render_hsv_block(key, detector)


def render_hsv_block(key: str, detector: HSVDetector):
    header_state = {'text': ''}

    def _header_text() -> str:
        alias = key or '未命名'
        return f'{alias} · hsv'

    def _refresh_header():
        header_state['text'] = _header_text()

    # ---- 事件处理：把滑条值写回配置，并更新右侧数值显示 ----
    def on_hmin(v):  cfg.h_min = int(v or 0);              hmin_value.text  = f"{cfg.h_min:d}"
    def on_hmax(v):  cfg.h_max = int(v or 0);              hmax_value.text  = f"{cfg.h_max:d}"
    def on_smin(v):  cfg.s_min = int(v or 0);              smin_value.text  = f"{cfg.s_min:d}"
    def on_vmin(v):  cfg.v_min = int(v or 0);              vmin_value.text  = f"{cfg.v_min:d}"
    def on_gmin(v):  cfg.g_min = int(v or 0);              gmin_value.text  = f"{cfg.g_min:d}"
    def on_gdom(v):  cfg.g_dom_ratio = float(v or 0);      gdom_value.text  = f"{cfg.g_dom_ratio:.2f}"
    def on_min_area(v): cfg.min_area = int(v or 1);        min_area_value.text = f"{cfg.min_area:d}"
    def on_max_area(v): cfg.max_area = int(v or 1);        max_area_value.text = f"{cfg.max_area:d}"
    def on_circ(v):  cfg.circularity_min = float(v or 0);  circ_value.text  = f"{cfg.circularity_min:.2f}"
    def on_open(v):  cfg.open_kernel = int(v or 1);        open_value.text  = f"{cfg.open_kernel:d}"
    def on_maxres(v): 
        cfg.max_results = int(v or 0)
        maxres_value.text = f"{cfg.max_results:d}"

    def on_apply_hsv():
        detector.update_config(cfg)
        logger.info(f'{key} 的 HSV 检测器配置已更新')

    _refresh_header()
    with ui.expansion(value=False).classes('w-full q-mb-md') as exp:
        with exp.add_slot('header'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('adjust')  # 圆形图标
                ui.label().bind_text_from(header_state, 'text')

        cfg = detector.get_config()
        with ui.card():
            ui.label('HSV 参数').classes('text-h6')
            with ui.column().classes('q-gutter-xs'):
                # 色相/饱和/亮度
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('H min').style('min-width:110px')
                    ui.slider(value=cfg.h_min, min=0, max=179, step=1,
                              on_change=lambda e: on_hmin(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    hmin_value = ui.label(f"{cfg.h_min:d}").style('min-width:48px;text-align:right')
                    ui.label('色相下限 (0..179)').style('color:#888;font-size:13px')
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('H max').style('min-width:110px')
                    ui.slider(value=cfg.h_max, min=0, max=179, step=1,
                              on_change=lambda e: on_hmax(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    hmax_value = ui.label(f"{cfg.h_max:d}").style('min-width:48px;text-align:right')
                    ui.label('色相上限 (0..179)').style('color:#888;font-size:13px')
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('S min').style('min-width:110px')
                    ui.slider(value=cfg.s_min, min=0, max=255, step=1,
                              on_change=lambda e: on_smin(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    smin_value = ui.label(f"{cfg.s_min:d}").style('min-width:48px;text-align:right')
                    ui.label('饱和度下限 (0..255)').style('color:#888;font-size:13px')
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('V min').style('min-width:110px')
                    ui.slider(value=cfg.v_min, min=0, max=255, step=1,
                              on_change=lambda e: on_vmin(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    vmin_value = ui.label(f"{cfg.v_min:d}").style('min-width:48px;text-align:right')
                    ui.label('亮度下限 (0..255)').style('color:#888;font-size:13px')

                # 绿色优势与强度
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('G min').style('min-width:110px')
                    ui.slider(value=cfg.g_min, min=0, max=255, step=1,
                              on_change=lambda e: on_gmin(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    gmin_value = ui.label(f"{cfg.g_min:d}").style('min-width:48px;text-align:right')
                    ui.label('绿色通道强度下限').style('color:#888;font-size:13px')
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('G / max(R,B)').style('min-width:110px')
                    ui.slider(value=cfg.g_dom_ratio, min=1.0, max=2.0, step=0.05,
                              on_change=lambda e: on_gdom(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    gdom_value = ui.label(f"{cfg.g_dom_ratio:.2f}").style('min-width:48px;text-align:right')
                    ui.label('绿色优势比阈值').style('color:#888;font-size:13px')

                # 形态与面积/圆度
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('min_area').style('min-width:110px')
                    ui.slider(value=cfg.min_area, min=1, max=2000, step=1,
                              on_change=lambda e: on_min_area(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    min_area_value = ui.label(f"{cfg.min_area:d}").style('min-width:48px;text-align:right')
                    ui.label('最小连通域面积').style('color:#888;font-size:13px')
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('max_area').style('min-width:110px')
                    ui.slider(value=cfg.max_area, min=10, max=20000, step=10,
                              on_change=lambda e: on_max_area(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    max_area_value = ui.label(f"{cfg.max_area:d}").style('min-width:48px;text-align:right')
                    ui.label('最大连通域面积').style('color:#888;font-size:13px')
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('circularity_min').style('min-width:110px')
                    ui.slider(value=cfg.circularity_min, min=0.0, max=1.0, step=0.05,
                              on_change=lambda e: on_circ(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    circ_value = ui.label(f"{cfg.circularity_min:.2f}").style('min-width:48px;text-align:right')
                    ui.label('圆度阈值 4πA/P²').style('color:#888;font-size:13px')
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('open_kernel').style('min-width:110px')
                    ui.slider(value=cfg.open_kernel, min=1, max=15, step=1,
                              on_change=lambda e: on_open(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    open_value = ui.label(f"{cfg.open_kernel:d}").style('min-width:48px;text-align:right')
                    ui.label('形态学开运算核大小 (去噪)').style('color:#888;font-size:13px')

                # 输出数量
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label('max_results').style('min-width:110px')
                    ui.slider(value=cfg.max_results, min=0, max=50, step=1,
                              on_change=lambda e: on_maxres(e.value)
                              ).style('min-width:240px;max-width:400px;flex:1')
                    maxres_value = ui.label(f"{cfg.max_results:d}").style('min-width:48px;text-align:right')
                    ui.label('0 表示不限制数量').style('color:#888;font-size:13px')

        ui.button('应用配置', on_click=on_apply_hsv, color='primary')