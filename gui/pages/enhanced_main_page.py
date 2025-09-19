from nicegui import ui
from core.logger import logger
from tasks.run_tasks import (
    start_step_thread,
    force_stop_current_task,
    is_task_running,
    start_default_full_process_thread,
    start_full_process_thread,
)
from tasks.debug_vars_enhanced import (
    get_enhanced_vars,
    get_enhanced_images,
    get_debug_summary,
    DebugLevel,
    DebugCategory,
)
from gui.utils import get_empty_img, prepare_image_for_display

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def get_level_color(level: DebugLevel) -> str:
    return {
        DebugLevel.INFO: "blue",
        DebugLevel.WARNING: "orange",
        DebugLevel.ERROR: "red",
        DebugLevel.SUCCESS: "green",
    }.get(level, "gray")


# -----------------------------------------------------------------------------
# Main entry
# -----------------------------------------------------------------------------

def render_enhanced_main_page():
    ui.markdown('# RoboGame2025')
    render_tasks_panel()
    ui.separator()
    render_debug_panel()


# -----------------------------------------------------------------------------
# Tasks Panel (simplified)
# -----------------------------------------------------------------------------


def render_tasks_panel():
    from tasks.run_tasks import _STEP_CLASSES  # lazy import to avoid cycles
    from core.config.tasks_config import load_tasks_config, save_tasks_config
    import inspect

    ui.markdown('## 控制面板')

    # === 载入配置 ===
    cfg = load_tasks_config()

    def _cfg_tasks_to_state():
        """把 dataclass/list 转为 UI 可编辑的 dict 列表"""
        items = getattr(cfg, 'tasks', []) or []
        out = []
        for t in items:
            if isinstance(t, dict):
                name = t.get('name', '')
                params = t.get('parameters', {}) or {}
            else:
                # dataclass StepConfig(name, parameters)
                name = getattr(t, 'name', '')
                params = getattr(t, 'parameters', {}) or {}
            out.append({'name': name, 'parameters': params})
        return out

    tasks_state = _cfg_tasks_to_state()

    # === 单步运行卡片（平铺），参数默认值会被配置里的 parameters 预填 ===
    step_params: dict[str, dict[str, object]] = {}
    step_cards: dict[str, ui.button] = {}

    def create_param_input(param_name: str, param: inspect.Parameter, preset_value=None):
        """根据步骤的参数类型生成控件"""
        default_value = param.default if param.default != inspect._empty else None
        param_type = param.annotation if param.annotation != inspect._empty else type(default_value)
        init_val = preset_value if preset_value is not None else default_value

        # number (float or int)
        if param_type in (float, int) or isinstance(init_val, (int, float)):
            fmt = '%.3f' if isinstance(init_val, float) else '%.0f'
            return ui.number(label=param_name, value=init_val, format=fmt).props('dense outlined size=sm').classes('w-36 min-w-36')
        # bool
        if param_type is bool or isinstance(init_val, bool):
            return ui.checkbox(text=param_name, value=bool(init_val or False)).props('dense')
        # fallback: string
        return ui.input(label=param_name, value='' if init_val is None else str(init_val)).props('dense outlined size=sm').classes('w-48 min-w-48')

    def _get_preset_map_for_step(step_name: str) -> dict:
        """从配置 tasks 中找到该步骤的 parameters 作为预置值"""
        for item in tasks_state:
            if item.get('name') == step_name and isinstance(item.get('parameters'), dict):
                return item['parameters']
        return {}
    

    def render_step_card(step_name: str):
        """单行平铺：左=名称，中=参数，右=运行按钮；参数用配置里同名步骤的 parameters 预填"""
        step_class = _STEP_CLASSES[step_name]
        sig = inspect.signature(step_class.__init__)
        preset_map = _get_preset_map_for_step(step_name)
        
        def _on_run_step_click(step_name: str):
            """执行单个步骤，使用用户输入的参数"""
            if is_task_running():
                ui.notify('已有任务在运行中，请先停止当前任务', type='warning')
                return
            
            # 收集步骤参数
            kwargs = {}
            for pname, widget in step_params.get(step_name, {}).items():
                if hasattr(widget, 'value'):
                    val = getattr(widget, 'value', None)
                    if val is not None and val != '':
                        kwargs[pname] = val

            try:
                logger.info(f'开始运行步骤: {step_name}, 参数: {kwargs}')
                start_step_thread(step_name, **kwargs)  # 启动步骤线程
                ui.notify(f'{step_name} 已启动', type='positive')
                # 立即更新按钮状态
                step_cards[step_name].props('loading')
                stop_btn.props('disable=false')
            except Exception as e:
                logger.error(f'启动步骤失败: {e}')
                ui.notify(f'启动失败: {e}', type='negative')  # 异常处理

        with ui.card().classes('w-full mb-2 hover:shadow transition-all'):
            with ui.card_section().classes('p-3'):
                with ui.row().classes('items-center w-full gap-3 no-wrap'):
                    # 左：名称
                    ui.label(step_name).classes('font-bold text-base text-blue-700 shrink-0 min-w-40 max-w-64 truncate')

                    # 中：参数（单行横向，可滚动）
                    params_row = ui.row().classes('items-center gap-2 no-wrap overflow-x-auto flex-1')
                    with params_row:
                        step_params[step_name] = {}
                        for param_name, param in sig.parameters.items():
                            if param_name == 'self':
                                continue
                            pv = preset_map.get(param_name)
                            w = create_param_input(param_name, param, preset_value=pv)
                            step_params[step_name][param_name] = w

                    # 右：运行按钮
                    with ui.row().classes('items-center justify-end shrink-0'):
                        btn = ui.button('运行', color='primary', icon='play_arrow').classes('text-sm px-3')
                        step_cards[step_name] = btn
                        btn.on('click', lambda e, n=step_name: _on_run_step_click(n))

    with ui.expansion('单步骤调试', icon='list_alt', value=True).classes('w-full mt-2'):
        ui.label('每个步骤可自定义参数；修改后点击“运行”').classes('text-sm text-gray-600 mb-2')
        with ui.grid(columns=1).classes('w-full gap-2 items-stretch'):
            for step_name in _STEP_CLASSES.keys():
                render_step_card(step_name)

    # === 配置编辑区：按顺序执行的任务列表 ===
    ui.separator().classes('my-3')
    ui.label('任务配置（顺序与参数）').classes('text-md font-bold text-blue-600')
    ui.label('配置要按顺序执行的任务步骤，每个步骤可以设置不同的参数').classes('text-sm text-gray-600 mb-2')

    items_container = ui.column().classes('w-full gap-2')
    step_choices = list(_STEP_CLASSES.keys())

    def _current_sequence_names():
        return [t['name'] for t in tasks_state if t.get('name')]

    def render_items():
        items_container.clear()
        for idx, item in enumerate(tasks_state):
            with items_container:
                with ui.card().classes('w-full mb-2 hover:shadow transition-all'):
                    with ui.card_section().classes('p-3'):
                        with ui.row().classes('items-center w-full gap-3 no-wrap'):
                            # 左：序号
                            ui.badge(str(idx + 1)).classes('shrink-0 text-base font-bold')
                            
                            # 中左：步骤选择
                            sel = ui.select(step_choices, value=item.get('name'), label='步骤', clearable=False).props('dense outlined').classes('w-48 shrink-0')
                            
                            # 步骤改变时重新渲染参数
                            def on_step_change(e, item_idx=idx):
                                if item_idx < len(tasks_state):
                                    tasks_state[item_idx]['name'] = e.value
                                    tasks_state[item_idx]['parameters'] = {}  # 清空参数
                                    render_items()
                            
                            sel.on('update:model-value', on_step_change)
                            
                            # 中右：参数（横向一行显示）
                            params_row = ui.row().classes('items-center gap-2 no-wrap overflow-x-auto flex-1')
                            param_widgets = {}
                            
                            current_step_name = item.get('name')
                            if current_step_name and current_step_name in _STEP_CLASSES:
                                step_class = _STEP_CLASSES[current_step_name]
                                sig = inspect.signature(step_class.__init__)
                                
                                with params_row:
                                    for param_name, param in sig.parameters.items():
                                        if param_name == 'self':
                                            continue
                                        
                                        current_value = item.get('parameters', {}).get(param_name)
                                        widget = create_param_input(param_name, param, preset_value=current_value)
                                        param_widgets[param_name] = widget
                            
                            # 右：控制按钮
                            with ui.row().classes('items-center justify-end shrink-0 gap-1'):
                                ui.button(icon='arrow_upward', on_click=lambda e, i=idx: (_move_up(i), render_items())).props('dense flat size=sm').classes('text-xs')
                                ui.button(icon='arrow_downward', on_click=lambda e, i=idx: (_move_down(i), render_items())).props('dense flat size=sm').classes('text-xs')
                                ui.button(icon='delete', color='negative', on_click=lambda e, i=idx: (_delete(i), render_items())).props('dense flat size=sm').classes('text-xs')
                
                # 保存引用，保存时读取
                item['__sel'] = sel
                item['__param_widgets'] = param_widgets

    def _move_up(i): 
        if i > 0: tasks_state[i-1], tasks_state[i] = tasks_state[i], tasks_state[i-1]

    def _move_down(i):
        if i < len(tasks_state) - 1: tasks_state[i+1], tasks_state[i] = tasks_state[i], tasks_state[i+1]

    def _delete(i):
        tasks_state.pop(i)

    def _add_item():
        tasks_state.append({'name': (step_choices[0] if step_choices else ''), 'parameters': {}})
        render_items()

    def _save_items():
        # 读取 UI -> 写回并保存
        new_list = []
        for idx, item in enumerate(tasks_state, start=1):
            name = item.get('__sel').value if item.get('__sel') else item.get('name')
            
            # 从参数widget收集参数
            params = {}
            param_widgets = item.get('__param_widgets', {})
            for param_name, widget in param_widgets.items():
                if hasattr(widget, 'value'):
                    val = getattr(widget, 'value', None)
                    if val is not None and val != '':
                        params[param_name] = val
            
            new_list.append({'name': name, 'parameters': params})
        
        # 保存
        try:
            cfg.tasks = new_list
            save_tasks_config(cfg)
            ui.notify('任务配置已保存', type='positive')
        except Exception as e:
            ui.notify(f'保存失败: {e}', type='negative')

    with ui.row().classes('gap-2 mt-1'):
        ui.button('新增步骤', icon='add', on_click=lambda e: _add_item()).props('dense')
        ui.button('保存配置', color='primary', icon='save', on_click=lambda e: _save_items()).props('dense')

    # 初次渲染（若为空则给一行模板）
    if not tasks_state:
        tasks_state.append({'name': next(iter(_STEP_CLASSES.keys()), ''), 'parameters': {}})
    render_items()
            
    def _update_button_states():
        """更新所有按钮的状态"""
        if is_task_running():
            # 任务运行时，所有运行按钮显示loading状态
            for btn in step_cards.values():
                btn.props('loading')
            run_full_btn.props('loading')
            stop_btn.props('disable=false')
        else:
            # 任务停止时，恢复正常状态
            for btn in step_cards.values():
                btn.props('loading=false')
            run_full_btn.props('loading=false')
            stop_btn.props('disable=true')

    def _on_run_config_sequence_click():
        """运行配置的顺序任务"""
        if is_task_running():
            ui.notify('已有任务在运行中，请先停止当前任务', type='warning')
            return
        
        # 获取当前配置的任务数量
        task_count = len([t for t in tasks_state if t.get('name')])
        if task_count == 0:
            ui.notify('没有配置任何任务，请先添加任务', type='warning')
            return
        
        try:
            logger.info(f'开始运行配置顺序任务，共 {task_count} 个步骤')
            start_default_full_process_thread()
            ui.notify(f'配置顺序任务已启动 (共{task_count}个步骤)', type='positive')
            # 立即更新按钮状态
            run_full_btn.props('loading')
            stop_btn.props('disable=false')
        except Exception as e:
            logger.error(f'启动配置顺序任务失败: {e}')
            ui.notify(f'启动失败: {e}', type='negative')

    def _on_stop_click():
        """强制停止当前任务"""
        if not is_task_running():
            ui.notify('当前没有正在运行的任务', type='info')
            return
        
        logger.info('用户请求强制停止当前任务')
        ui.notify('正在强制停止任务并执行清理...', type='warning', timeout=3000)
        
        try:
            force_stop_current_task()
            ui.notify('任务已强制停止，清理完成', type='positive')
        except Exception as e:
            logger.error(f'强制停止过程中出现异常: {e}')
            ui.notify(f'停止失败: {e}', type='negative')
        finally:
            # 立即更新按钮状态
            run_full_btn.props('loading=false')
            stop_btn.props('disable=true')
            for btn in step_cards.values():
                btn.props('loading=false')

    with ui.row().classes('gap-2 w-full'):
        run_full_btn = ui.button('运行配置顺序', color='secondary', icon='play_arrow')
        run_full_btn.on('click', _on_run_config_sequence_click)
        
        stop_btn = ui.button('强制停止', color='negative', icon='stop').props('disable=true')
        stop_btn.on('click', _on_stop_click)
    
    # 定时更新按钮状态
    ui.timer(1.0, _update_button_states)




# -----------------------------------------------------------------------------
# Debug Panel (simplified)
# -----------------------------------------------------------------------------

def render_debug_panel():
    ui.markdown('## 调试参数')

    # Images row (max 2)
    with ui.card().classes('w-full mb-3'):
        with ui.row().classes('flex-wrap gap-2 p-2'):
            empty_img = get_empty_img()
            img1 = ui.interactive_image(empty_img).classes('rounded-borders')
            img2 = ui.interactive_image(empty_img).classes('rounded-borders')

    # Vars as tabs to reduce clutter
    with ui.tabs() as tabs:
        t_status = ui.tab('状态')
        t_detect = ui.tab('检测')
        t_position = ui.tab('位置')
        t_control = ui.tab('控制')
        t_timing = ui.tab('时间')
        t_error = ui.tab('错误')

    with ui.tab_panels(tabs, value=t_status).classes('w-full'):
        p_status = ui.tab_panel(t_status)
        p_detect = ui.tab_panel(t_detect)
        p_position = ui.tab_panel(t_position)
        p_control = ui.tab_panel(t_control)
        p_timing = ui.tab_panel(t_timing)
        p_error = ui.tab_panel(t_error)

    containers = {
        DebugCategory.STATUS: p_status,
        DebugCategory.DETECTION: p_detect,
        DebugCategory.POSITION: p_position,
        DebugCategory.CONTROL: p_control,
        DebugCategory.TIMING: p_timing,
        DebugCategory.ERROR: p_error,
    }

    def refresh():
        vars_data = get_enhanced_vars()
        images_data = get_enhanced_images()
        _ = get_debug_summary()  # kept for parity; could be shown if needed

        # update images
        items = list(images_data.items())[:2]
        try:
            if len(items) > 0:
                img1.set_source(prepare_image_for_display(items[0][1].image))
            if len(items) > 1:
                img2.set_source(prepare_image_for_display(items[1][1].image))
        except Exception as e:
            logger.warning(f'更新图像失败: {e}')

        # update vars per category
        for cat, panel in containers.items():
            panel.clear()
            cat_vars = {k: v for k, v in vars_data.items() if v.category == cat}
            if not cat_vars:
                with panel:
                    ui.label('暂无数据').classes('text-gray-500 text-sm p-2')
                continue
            with panel:
                for k, entry in cat_vars.items():
                    color = get_level_color(entry.level)
                    with ui.row().classes('items-center mb-1 p-2 bg-gray-50 rounded'):
                        ui.badge(entry.level.value, color=color).classes('mr-2')
                        with ui.column().classes('flex-grow'):
                            ui.label(f'{k}: {entry.value}').classes('font-medium text-sm')
                            if entry.description:
                                ui.label(entry.description).classes('text-xs text-gray-600')
                            ui.label(entry.timestamp.strftime('%H:%M:%S')).classes('text-xs text-gray-400')

    ui.timer(0.5, refresh)
