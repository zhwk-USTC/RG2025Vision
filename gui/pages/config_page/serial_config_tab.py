from typing import List, Dict, Optional
import binascii
import asyncio
from serial.tools import list_ports
from nicegui import ui
from core.logger import logger
from communicate import (
start_serial, stop_serial, 
scan_serial_ports, get_serial,
save_serial_config, 
select_serial_port,
ports_list
)

def render_serial_config_tab() -> None:
    def on_save_config():
        save_serial_config()
        logger.info('串口配置已保存')
        

    async def on_connect_click():
        start_serial()

    async def on_disconnect_click():
        stop_serial()

    def on_select_serial(port: Optional[str]):
        if port:
            select_serial_port(port)
            logger.info(f'已选择串口: {port}')
        else:
            logger.warning('未选择串口')

    ports = ports_list()
    port_options = {port.device: str(port) for port in ports}

    # 获取当前配置的端口，如果不在选项中则设为None
    current_port = get_serial().cfg.port
    if current_port not in port_options:
        current_port = None

    # ---- UI ----
    with ui.row():
        save_button = ui.button('保存配置', color='secondary', on_click=lambda e: on_save_config())
        def on_scan_serial_ports():
            try:
                scan_serial_ports()
                logger.info('串口扫描完成')
                # 延迟一点时间让用户看到提示，然后刷新页面
                ui.timer(1.0, lambda: ui.navigate.reload(), once=True)
            except Exception as e:
                ui.notify(f'串口扫描失败: {e}', type='negative')
                logger.error(f'串口扫描失败: {e}')
        scan_serial_button = ui.button(
            '扫描串口', color='primary', on_click=on_scan_serial_ports)
    with ui.row():
        port_select = ui.select(
            options=port_options,
            value=current_port,
            label='端口',
            on_change=lambda e: on_select_serial(e.value),
        ).classes('w-64')
    with ui.row().classes('items-center gap-3'):
        
        connect_btn = ui.button(
            '连接', color='primary', on_click=on_connect_click)
        disconnect_btn = ui.button(
            '断开', color='negative', on_click=on_disconnect_click)
