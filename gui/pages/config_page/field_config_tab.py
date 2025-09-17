from nicegui import ui
from core.logger import logger


def render_field_config_tab():
    """场地配置Tab"""
    from core.config.field_config import (
        get_field_manager, get_current_field, set_current_field,
        list_available_fields, save_field_config
    )
    
    ui.label('场地配置管理').classes('text-h6')
    
    # 当前场地显示
    with ui.card().classes('q-pa-md'):
        current_field = get_current_field()
        ui.label(f'当前场地: {current_field.name}').classes('text-subtitle1')
        ui.label(f'描述: {current_field.description}').classes('text-body2')
        
        if current_field.firespot_tag:
            ui.label(f'发射架Tag ID: {current_field.firespot_tag.tag_id}').classes('text-body2')
    
    # 场地切换
    with ui.card().classes('q-pa-md q-mt-md'):
        ui.label('切换场地').classes('text-subtitle2')
        fields = list_available_fields()
        
        def on_field_change(field_key):
            if set_current_field(field_key):
                ui.notify(f'已切换到场地: {fields[field_key]}', type='positive')
                # 刷新页面或重新渲染当前字段显示
            else:
                ui.notify('切换失败', type='negative')
        
        ui.select(
            options=fields,
            label='选择场地',
            on_change=lambda e: on_field_change(e.value) if e.value else None
        )
