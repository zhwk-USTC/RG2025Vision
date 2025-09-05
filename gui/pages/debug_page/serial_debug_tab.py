from typing import Optional
import binascii
from nicegui import ui
from core.logger import logger

from communicate import (
    AsyncSerial,
    start_serial, stop_serial,
    scan_serial_ports, get_serial,
    save_serial_config, select_serial_port,
    ports_list,
    get_latest_frame,   # ← communicate(serial_app) 里暴露
    send_kv,            # ← communicate(serial_app) 里暴露（内部会封帧+发送）
    Var
)

def _hex(b: bytes, sep: str = ' ') -> str:
    if not b:
        return ''
    h = binascii.hexlify(b).decode('ascii')
    return sep.join(h[i:i+2] for i in range(0, len(h), 2))


def _fmt_decoded(decoded) -> str:
    """
    友好打印 DataPacket（若可用）:
    MSG=x VER=y
      - T=0x.. L=n V=....
    """
    if decoded is None:
        return '(no decoded data)'
    try:
        msg = getattr(decoded, 'msg', None)
        ver = getattr(decoded, 'ver', None)
        tlvs = getattr(decoded, 'tlvs', None)
        if msg is None or ver is None or tlvs is None:
            return str(decoded)
        def _as_int(x):
            try:
                return int(x)
            except Exception:
                return x
        lines = [f"MSG={_as_int(msg)} VER={int(ver)}"]
        for tlv in tlvs:
            t = getattr(tlv, 't', None)
            v = getattr(tlv, 'v', None)
            if t is None or v is None:
                continue
            t_disp = _as_int(t)
            v_bytes = bytes(v)
            lines.append(f"  - T=0x{t_disp:02X} L={len(v_bytes)} V={_hex(v_bytes)}")
        return '\n'.join(lines)
    except Exception:
        return str(decoded)


def render_serial_tab() -> None:
    # ----------------- 顶部串口控制 -----------------
    def on_save_config():
        save_serial_config()
        ui.notify('串口配置已保存', color='positive')
        logger.info('串口配置已保存')

    async def on_connect_click():
        await start_serial()
        ui.notify('串口已连接', color='positive')

    async def on_disconnect_click():
        await stop_serial()
        ui.notify('串口已断开', color='warning')

    def on_select_serial(port: Optional[str]):
        if port:
            select_serial_port(port)
            logger.info(f'已选择串口: {port}')
        else:
            logger.warning('未选择串口')

    ports = ports_list()
    port_options = {port.device: str(port) for port in ports}

    with ui.row():
        ui.button('保存配置', color='secondary', on_click=lambda e: on_save_config())
        ui.button('扫描串口', color='primary', on_click=lambda e: scan_serial_ports())

    with ui.row():
        ui.select(
            options=port_options,
            value=get_serial().port,
            label='端口',
            on_change=lambda e: on_select_serial(e.value),
        ).classes('w-64')

    with ui.row().classes('items-center gap-3'):
        ui.button('连接', color='primary', on_click=on_connect_click)
        ui.button('断开', color='negative', on_click=on_disconnect_click)

    ui.separator()

    # ----------------- 接收监视：只读展示 -----------------
    with ui.card().classes('w-full'):
        ui.label('接收监视（只读）').classes('text-lg font-semibold')

        status_label = ui.label('状态：空').classes('text-gray-500')

        with ui.row().classes('w-full'):
            with ui.column().classes('w-full'):
                ui.label('完整帧（AA ... 55）').classes('text-sm text-gray-600')
                frame_area = ui.textarea(value='', placeholder='hex view')\
                               .props('rows=4 readonly').classes('w-full font-mono text-xs')
            with ui.column().classes('w-full'):
                ui.label('DATA 区（十六进制）').classes('text-sm text-gray-600')
                data_area = ui.textarea(value='', placeholder='hex view')\
                              .props('rows=4 readonly').classes('w-full font-mono text-xs')

        ui.label('DATA 解析（MSG/VER/TLVs）').classes('text-sm text-gray-600')
        decoded_area = ui.textarea(value='(no data)', placeholder='decoded view')\
                         .props('rows=6 readonly').classes('w-full font-mono text-xs')

        def clear_view():
            status_label.set_text('状态：已清空（仅界面）')
            frame_area.set_value('')
            data_area.set_value('')
            decoded_area.set_value('(no data)')

        with ui.row().classes('justify-end w-full'):
            ui.button('清空显示', color='secondary', on_click=lambda e: clear_view())

        async def refresh_view():
            try:
                frame_bytes, data_bytes, decoded = await get_latest_frame()
                if frame_bytes:
                    status_label.set_text(
                        f'状态：已接收 | frame={len(frame_bytes)}B | data={len(data_bytes)}B'
                    )
                    frame_area.set_value(_hex(frame_bytes))
                    data_area.set_value(_hex(data_bytes))
                    decoded_area.set_value(_fmt_decoded(decoded))
                else:
                    status_label.set_text('状态：空')
            except Exception as e:
                logger.warning(f'[GUI] 刷新接收监视失败: {e}')

        ui.timer(0.2, refresh_view)



    # ----------------- 发送测试帧（U8 / U16 / F32） -----------------
    with ui.card().classes('w-full'):
        ui.label('发送测试帧（可多选变量）').classes('text-lg font-semibold')

        with ui.row().classes('items-center gap-6'):
            cb_u8 = ui.checkbox('test_var_u8').props('dense')
            num_u8 = ui.number('U8 值 (0..255)', value=1, min=0, max=255, step=1).classes('w-56')

            cb_u16 = ui.checkbox('test_var_u16').props('dense')
            num_u16 = ui.number('U16 值 (0..65535)', value=300, min=0, max=65535, step=1).classes('w-56')

            cb_f32 = ui.checkbox('test_var_f32').props('dense')
            num_f32 = ui.number('F32 值', value=3.14, step=0.01).classes('w-56')

        async def on_send_selected():
            try:
                kv = {}
                if cb_u8.value:
                    kv[Var.TEST_VAR_U8] = int(num_u8.value) & 0xFF
                if cb_u16.value:
                    kv[Var.TEST_VAR_U16] = int(num_u16.value) & 0xFFFF
                if cb_f32.value:
                    # 直接传 float；data.py 内部会按 float32 小端打包
                    kv[Var.TEST_VAR_F32] = float(num_f32.value)

                if not kv:
                    ui.notify('请先选择至少一个变量', color='warning')
                    return

                await send_kv(kv)
                ui.notify('测试帧已发送', color='positive')
            except Exception as e:
                logger.warning(f'[GUI] 发送测试帧失败: {e}')
                ui.notify(f'发送失败: {e}', color='negative')

        with ui.row().classes('items-center gap-3'):
            ui.button('发送所选', color='accent', on_click=on_send_selected)

            # 快捷按钮：只发某一个变量
            async def send_only_u8():
                await send_kv({Var.TEST_VAR_U8: int(num_u8.value) & 0xFF})
                ui.notify('已发送: test_var_u8', color='positive')

            async def send_only_u16():
                await send_kv({Var.TEST_VAR_U16: int(num_u16.value) & 0xFFFF})
                ui.notify('已发送: test_var_u16', color='positive')

            async def send_only_f32():
                await send_kv({Var.TEST_VAR_F32: float(num_f32.value)})
                ui.notify('已发送: test_var_f32', color='positive')

            ui.button('只发 U8', on_click=send_only_u8)
            ui.button('只发 U16', on_click=send_only_u16)
            ui.button('只发 F32', on_click=send_only_f32)

    ui.separator()