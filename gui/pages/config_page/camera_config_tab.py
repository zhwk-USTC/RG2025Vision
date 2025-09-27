from nicegui import ui
import numpy as np
from typing import Optional
from PIL import Image

from vision import get_vision, save_vision_config
from vision.camera import get_camera_info_list, Camera, scan_cameras
from core.logger import logger
import cv2


def _empty_image():
    return Image.fromarray(np.zeros((480, 640, 3), dtype=np.uint8))


def render_camera_config_tab():
    vs = get_vision()

    def on_save_config():
        save_vision_config()

    def on_scan_cameras():
        try:
            scan_cameras()
            logger.info('摄像头扫描完成')
            ui.timer(1.0, lambda: ui.navigate.reload(), once=True)
        except Exception as e:
            logger.error(f'摄像头扫描失败: {e}')

    with ui.row():
        ui.button('保存配置', color='secondary', on_click=lambda e: on_save_config())
        ui.button('扫描摄像头', color='primary', icon='camera_alt', on_click=lambda e: on_scan_cameras())
    # 默认：可独立展开多个
    for key, cam in vs._cameras.items():
        render_camera_block(key, cam)

def render_camera_block(key: str, cam: Camera):
    cam_info_list = get_camera_info_list()
    cam_choices = {c.index: c.name for c in cam_info_list}

    # ---- 头部状态 ----
    header_state = {'text': ''}

    def _header_text() -> str:
        alias = key or '未命名'
        name = cam.name or '未选择'
        idx = cam.index if cam.index is not None else '未选择'
        return f'{alias} · {name} · index={idx}'

    def _refresh_header():
        header_state['text'] = _header_text()

    # ---- 事件处理 ----
    def on_camera_change(index: int):
        cam.select_by_index(index)
        logger.info(f'{key} 已选择摄像头 {cam.name} (index={index})')
        _refresh_header()

    def on_width_change(value: int):
        cam.width = value
        logger.info(f'摄像头 {cam.name} 的宽度已更改为 {value}')

    def on_height_change(value: int):
        cam.height = value
        logger.info(f'摄像头 {cam.name} 的高度已更改为 {value}')

    def on_fps_change(value: int):
        cam.fps = value
        logger.info(f'摄像头 {cam.name} 的帧率已更改为 {value}')

    def on_connect_camera():
        cam.connect()
        logger.info(f'摄像头 {cam.name} 已连接')
        _refresh_header()

    def on_disconnect_camera():
        cam.disconnect()
        logger.info(f'摄像头 {cam.name} 已断开连接')
        _refresh_header()

    def on_refresh_image():
        try:
            frame = cam.read_frame()
            if frame is not None:
                img_widget.set_source(Image.fromarray(frame))
            else:
                img_widget.set_source(_empty_image())
            status_widget.set_content(cam.get_status())
        except Exception as e:
            logger.error(f'摄像头 {cam.name} 图像刷新失败: {e}')

    # ===== 自动刷新逻辑 =====
    _auto_timer = {'t': None}  # 保存 ui.timer 以便取消/重启

    def _tick():
        on_refresh_image()

    def _start_timer():
        fps = int(auto_fps.value or 10)
        fps = max(1, min(120, fps))
        _auto_timer['t'] = ui.timer(1.0 / fps, _tick)  # type: ignore
        logger.info(f'[{key}] 自动刷新已开启: {fps} FPS')

    def _stop_timer():
        if _auto_timer['t']:
            _auto_timer['t'].cancel()
            _auto_timer['t'] = None
            logger.info(f'[{key}] 自动刷新已停止')

    def on_auto_toggle(enabled: bool):
        if enabled:
            _start_timer()
        else:
            _stop_timer()

    def on_auto_fps_change(v):
        # 若正在自动刷新，则应用新的频率
        if _auto_timer['t']:
            _stop_timer()
            _start_timer()

    # ===== 专业参数事件处理 =====
    cfg = cam._config

    def _apply_now():
        try:
            if cam.is_open and hasattr(cam, "_apply_controls"):
                cam._apply_controls()  # type: ignore[attr-defined]
                logger.info(f'已应用 {cam.name} 专业参数')
            else:
                logger.info('设备未连接：已保存配置，连接后自动生效')
        except Exception as e:
            logger.warning(f'应用参数失败：{e}')
        status_widget.set_content(cam.get_status())

    # 快捷设定色温
    def set_wb_preset(k: int):
        cfg.wb_temperature = int(k)
        logger.info(f'预设色温: {k}K')
        if cam.is_open:
            cam._set_white_balance_smart()
            status_widget.set_content(cam.get_status())

    # ---- UI 构建（紧凑）----
    _refresh_header()
    with ui.expansion(value=False).classes('w-full q-mb-sm') as exp:
        with exp.add_slot('header'):
            with ui.row().classes('items-center gap-1'):
                ui.icon('videocam')
                ui.label().bind_text_from(header_state, 'text')

        with ui.card().classes('q-pa-sm w-full'):
            with ui.row().classes('w-full items-start gap-2 no-wrap'):
                # 左：基础参数（2列栅格）
                with ui.column().classes('q-gutter-xs').style('min-width: 340px'):
                    with ui.grid(columns=2).classes('items-center gap-2'):
                        initial_value = cam.index if cam.index in cam_choices else None
                        ui.select(
                            cam_choices,
                            value=initial_value,
                            label='选择',
                            on_change=lambda e: on_camera_change(e.value),
                        ).props('dense').classes('col-span-2')
                        ui.number(
                            label='宽度', value=cam.width, format='%.0f',
                            on_change=lambda e: on_width_change(int(e.value)) if e.value else None,
                        ).props('dense')
                        ui.number(
                            label='高度', value=cam.height, format='%.0f',
                            on_change=lambda e: on_height_change(int(e.value)) if e.value else None,
                        ).props('dense')
                        ui.number(
                            label='帧率', value=cam.fps, format='%.0f',
                            on_change=lambda e: on_fps_change(int(e.value)) if e.value else None,
                        ).props('dense')

                    with ui.row().classes('gap-1 q-mt-xs'):
                        ui.button('连接', color='primary', on_click=lambda e: on_connect_camera()).props('dense')
                        ui.button('断开', color='negative', on_click=lambda e: on_disconnect_camera()).props('dense')
                        ui.button('刷新', icon='refresh', on_click=lambda e: on_refresh_image()).props('dense')

                        # === 新增：自动刷新按钮 + FPS ===
                        auto_toggle = ui.checkbox('自动刷新', value=False,
                                                  on_change=lambda e: on_auto_toggle(bool(e.value))).props('dense')
                        auto_fps = ui.number('FPS', value=10, min=1, max=120, step=1,
                                             on_change=lambda e: on_auto_fps_change(e.value)).props('dense').classes('w-24')

                # 中：图像（小边距）
                with ui.column().classes('q-gutter-xs').style('min-width: 360px'):
                    img_widget = ui.interactive_image(_empty_image()).classes('rounded-borders')

                # 右：状态 + 内参 + 专业参数（2列栅格）
                with ui.column().classes('q-gutter-xs').style('min-width: 360px; max-width: 520px'):
                    status_widget = ui.code(cam.get_status()).props('readonly dense').classes('w-full')

                    # 显示相机内参
                    def get_intrinsics_text():
                        vs = get_vision()
                        try:
                            intrinsics = vs.get_camera_intrinsics(key)  # type: ignore
                            if intrinsics:
                                intrin_text = (
                                    f"fx={getattr(intrinsics, 'fx', 'N/A'):.2f}\n"
                                    f"fy={getattr(intrinsics, 'fy', 'N/A'):.2f}\n"
                                    f"cx={getattr(intrinsics, 'cx', 'N/A'):.2f}\n"
                                    f"cy={getattr(intrinsics, 'cy', 'N/A'):.2f}"
                                )
                            else:
                                intrin_text = "(无内参信息)"
                        except Exception as e:
                            intrin_text = f"(内参读取错误: {e})"
                        return intrin_text

                    intrinsics_widget = ui.code(get_intrinsics_text()).props('readonly dense').classes('w-full')
                    with ui.row().classes('items-center gap-2'):
                        ui.label('相机内参').classes('text-caption text-bold')

                    # 小工具：标题旁的问号提示
                    def info_tip(text: str):
                        ico = ui.icon('help').classes('text-grey-6 cursor-pointer')
                        ui.tooltip(text).classes('text-body2')
                        return ico

                    # --- 曝光/增益 ---
                    with ui.row().classes('items-center justify-start q-mtf-xs q-mb-none'):
                        ui.label('曝光 / 增益').classes('text-primary text-bold')
                        info_tip('建议：先关闭自动曝光(AE)再设定。Windows常用log2(秒)，Linux(V4L2)常用100μs为1单位。交流照明下优先选择与电网频率相关的快门以减轻频闪。')
                    with ui.grid(columns=2).classes('items-center gap-2'):
                        ui.switch('关AE', value=bool(cfg.auto_exposure_off),
                                  on_change=lambda e: setattr(cfg, 'auto_exposure_off', bool(e.value))
                                  ).props('dense').classes('col-span-1')
                        ui.number(label='曝光(raw)',
                                  value=cfg.exposure if cfg.exposure is not None else None,
                                  step=1,
                                  on_change=lambda e: setattr(cfg, 'exposure', float(e.value) if e.value else None)
                                  ).props('dense')
                        ui.number(label='增益',
                                  value=cfg.gain if cfg.gain is not None else None,
                                  step=1,
                                  on_change=lambda e: setattr(cfg, 'gain', float(e.value) if e.value else None)
                                  ).props('dense')
                    ui.label('提示：更长曝光+更低增益通常噪点更少；但需防抖与运动模糊。').classes('text-caption text-grey-6')
                    ui.button('写入曝光(在线)', color='primary',
                              on_click=lambda e: cam._set_exposure_smart()
                              ).props('dense').classes('col-span-2')

                    # --- 白平衡 ---
                    # with ui.row().classes('items-center justify-start q-mt-sm q-mb-none'):
                    #     ui.label('白平衡').classes('text-primary text-bold')
                    #     info_tip('关闭自动白平衡(AWB)后可设色温(K)。若设备不支持Kelvin，将自动回退为通道映射；此UI不做自动求增益。')
                    # with ui.grid(columns=2).classes('items-center gap-2'):
                    #     ui.switch('关AWB', value=bool(cfg.auto_wb_off),
                    #               on_change=lambda e: setattr(cfg, 'auto_wb_off', bool(e.value))
                    #               ).props('dense')
                    #     ui.number(label='色温(K)',
                    #               value=cfg.wb_temperature if cfg.wb_temperature is not None else None,
                    #               min=2800, max=6500, step=50,
                    #               on_change=lambda e: setattr(cfg, 'wb_temperature', int(e.value) if e.value else None)
                    #               ).props('dense')

                    # with ui.row().classes('gap-1'):
                    #     ui.button('室内(3200K)', on_click=lambda e: set_wb_preset(3200)).props('dense')
                    #     ui.button('日光(5600K)', on_click=lambda e: set_wb_preset(5600)).props('dense')

                    # ui.button('写入白平衡(在线)', color='primary',
                    #           on_click=lambda e: cam._set_white_balance_smart()
                    #           ).props('dense').classes('col-span-2')
                    # ui.label('提示：固定色温便于多相机一致与后处理复现。').classes('text-caption text-grey-6')
