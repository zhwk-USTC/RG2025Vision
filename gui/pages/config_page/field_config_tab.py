from nicegui import ui
from core.logger import logger
from core.config.field_config import TagConfig, FieldConfig


def render_field_config_tab():
    """场地配置Tab"""
    from core.config.field_config import (
        get_field_manager, get_current_field, set_current_field,
        list_available_fields, save_field_config, add_field, remove_field,
        add_tag
    )
    
    ui.label('场地配置管理').classes('text-h6')
    
    # 保存按钮
    with ui.row().classes('q-mb-md'):
        def on_save():
            save_field_config()
            ui.notify('场地配置已保存', type='positive')
        
        ui.button('保存配置', color='primary', icon='save', on_click=on_save)
    
    # 状态容器，用于刷新显示
    state = {'refresh_count': 0}
    
    def refresh_display():
        state['refresh_count'] += 1
        display_container.clear()
        with display_container:
            render_field_management()
            render_tag_management()
    
    def render_field_management():
        """渲染场地管理界面"""
        # 场地管理
        with ui.card().classes('q-pa-md'):
            ui.label('场地管理').classes('text-subtitle2')
            fields = list_available_fields()
            
            if fields:
                def on_field_change(field_key):
                    if field_key and set_current_field(field_key):
                        ui.notify(f'已切换到场地: {fields[field_key]}', type='positive')
                        refresh_display()
                    else:
                        ui.notify('切换失败', type='negative')
                
                current_manager = get_field_manager()
                current_value = current_manager.current_field if current_manager.current_field in fields else None
                
                with ui.row().classes('items-center gap-4'):
                    ui.select(
                        options=fields,
                        value=current_value,
                        label='选择场地',
                        on_change=lambda e: on_field_change(e.value) if e.value else None
                    ).classes('flex-grow').style('min-width: 200px')
                    
                    # 场地操作按钮
                    ui.button('新建场地', color='primary', on_click=lambda: show_add_field_dialog())
                    ui.button('删除场地', color='negative', on_click=lambda: show_delete_field_dialog())
            else:
                ui.label('没有可用的场地').classes('text-body2 text-grey-6')
                ui.button('新建场地', color='primary', on_click=lambda: show_add_field_dialog())

    def render_tag_management():
        """渲染Tag管理界面"""
        current_field = get_current_field()
        
        with ui.card().classes('q-pa-md q-mt-md'):
            ui.label('Tags管理').classes('text-subtitle2')
            
            # Tag列表显示
            tag_container = ui.column()
            
            def refresh_tags():
                tag_container.clear()
                with tag_container:
                    current = get_current_field()  # 重新获取最新数据
                    if current.tags:
                        ui.label('当前配置的Tags:').classes('text-body2 q-mb-sm')
                        for tag_name, tag_config in current.tags.items():
                            with ui.row().classes('items-center justify-between q-pa-sm bg-grey-1 rounded-borders q-mb-xs'):
                                with ui.column().classes('col-grow'):
                                    ui.label(f'{tag_name}').classes('text-subtitle2')
                                    tag_info = f'ID: {tag_config.tag_id} | 类型: {tag_config.tag_family} | 尺寸: {tag_config.tag_size}m'
                                    ui.label(tag_info).classes('text-body2 text-grey-7')
                                
                                def make_delete_handler(tag_name_to_delete):
                                    return lambda: delete_tag(tag_name_to_delete)
                                
                                ui.button('删除', color='negative', 
                                        on_click=make_delete_handler(tag_name))
                    else:
                        ui.label('当前场地没有配置任何Tags').classes('text-body2 text-grey-6')
            
            def delete_tag(tag_name: str):
                manager = get_field_manager()
                if manager.current_field in manager.fields:
                    if tag_name in manager.fields[manager.current_field].tags:
                        del manager.fields[manager.current_field].tags[tag_name]
                        # 移除自动保存，需要手动点击保存按钮
                        ui.notify(f'Tag "{tag_name}" 已删除', type='info')
                        refresh_tags()
            
            refresh_tags()
            
            # 添加新Tag界面
            ui.separator().classes('q-my-md')
            ui.label('添加新Tag').classes('text-body1')
            
            tag_name_ref = {'value': ''}
            tag_id_ref = {'value': 1}
            tag_family_ref = {'value': 'tag36h11'}
            tag_size_ref = {'value': 0.1}
            
            with ui.grid(columns=5).classes('gap-2 q-mt-sm'):
                ui.input('Tag名称', placeholder='如: firespot').bind_value(tag_name_ref, 'value')
                ui.number('Tag ID', value=1, min=0, max=999).bind_value(tag_id_ref, 'value')
                ui.select(['tag36h11', 'tag25h9'], value='tag36h11', label='Tag类型').bind_value(tag_family_ref, 'value')
                ui.number('尺寸(m)', value=0.1, min=0.01, max=1.0, step=0.01).bind_value(tag_size_ref, 'value')
            
            def add_new_tag():
                if tag_name_ref['value']:
                    new_tag = TagConfig(
                        tag_id=int(tag_id_ref['value']),
                        tag_family=tag_family_ref['value'],
                        tag_size=float(tag_size_ref['value']),
                    )
                    
                    if add_tag(tag_name_ref['value'], new_tag):
                        ui.notify(f'Tag "{tag_name_ref["value"]}" 添加成功', type='info')
                        # 清空输入
                        tag_name_ref['value'] = ''
                        tag_id_ref['value'] = 1
                        refresh_tags()
                    else:
                        ui.notify('添加失败', type='negative')
                else:
                    ui.notify('请输入Tag名称', type='warning')
            
            ui.button('添加Tag', color='primary', on_click=add_new_tag).classes('q-mt-sm')
    
    def show_add_field_dialog():
        """显示添加场地对话框"""
        field_name_ref = {'value': ''}
        field_key_ref = {'value': ''}
        
        with ui.dialog().props('persistent') as dialog:
            with ui.card().classes('q-pa-md'):
                ui.label('新建场地').classes('text-h6')
                ui.input('场地标识键', placeholder='如: field_c').bind_value(field_key_ref, 'value')
                ui.input('场地名称', placeholder='如: 比赛场地C').bind_value(field_name_ref, 'value')
                
                with ui.row().classes('justify-end gap-2 q-mt-md'):
                    ui.button('取消', on_click=dialog.close)
                    def on_create():
                        if field_key_ref['value'] and field_name_ref['value']:
                            new_field = FieldConfig(name=field_name_ref['value'])
                            add_field(field_key_ref['value'], new_field)
                            ui.notify(f'场地 "{field_name_ref["value"]}" 创建成功', type='positive')
                            dialog.close()
                            refresh_display()
                        else:
                            ui.notify('请填写完整信息', type='warning')
                    
                    ui.button('创建', color='primary', on_click=on_create)
        
        dialog.open()
    
    def show_delete_field_dialog():
        """显示删除场地确认对话框"""
        current_field = get_current_field()
        
        if not current_field.name or current_field.name == "无可用场地":
            ui.notify('没有可删除的场地', type='warning')
            return
        
        with ui.dialog().props('persistent') as dialog:
            with ui.card().classes('q-pa-md'):
                ui.label('确认删除').classes('text-h6')
                ui.label(f'确定要删除场地 "{current_field.name}" 吗？').classes('text-body1')
                ui.label('删除后将无法恢复！').classes('text-body2 text-negative')
                
                with ui.row().classes('justify-end gap-2 q-mt-md'):
                    ui.button('取消', on_click=dialog.close)
                    def on_delete():
                        manager = get_field_manager()
                        if remove_field(manager.current_field):
                            ui.notify(f'场地 "{current_field.name}" 已删除', type='positive')
                            dialog.close()
                            refresh_display()
                        else:
                            ui.notify('删除失败', type='negative')
                    
                    ui.button('确认删除', color='negative', on_click=on_delete)
        
        dialog.open()
    
    # 主显示容器
    display_container = ui.column()
    refresh_display()
