from typing import List, Dict, Optional
import binascii
import asyncio
from serial.tools import list_ports
from nicegui import ui
from core.logger import logger
from communicate import (AsyncSerial, 
start_serial, stop_serial, 
scan_serial_ports, init_serial, get_serial,
save_serial_config, 
select_serial_port,
ports_list
)

def render_serial_config_tab() -> None:
    def on_save_config():
        save_serial_config()
        logger.info('串口配置已保存')
        

    async def on_connect_click():
        await start_serial()

    async def on_disconnect_click():
        await stop_serial()

    def on_select_serial(port: Optional[str]):
        if port:
            select_serial_port(port)
            logger.info(f'已选择串口: {port}')
        else:
            logger.warning('未选择串口')

    ports = ports_list()
    port_options = {port.device: str(port) for port in ports}

    # ---- UI ----
    with ui.row():
        save_button = ui.button('保存配置', color='secondary', on_click=lambda e: on_save_config())
        scan_serial_button = ui.button(
            '扫描串口', color='primary', on_click=lambda e: scan_serial_ports())
    with ui.row():
        port_select = ui.select(
            options=port_options,
            value=get_serial().port,
            label='端口',
            on_change=lambda e: on_select_serial(e.value),
        ).classes('w-64')
    with ui.row().classes('items-center gap-3'):
        
        connect_btn = ui.button(
            '连接', color='primary', on_click=on_connect_click)
        disconnect_btn = ui.button(
            '断开', color='negative', on_click=on_disconnect_click)
