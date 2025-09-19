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

    ui.markdown('## 控制面板')

    # --- Top controls ---
    with ui.row().classes('gap-2 w-full'):
        run_full_btn = ui.button('运行完整流程', color='secondary', icon='play_arrow')
        run_full_custom_btn = ui.button('自定义全流程', color='accent', icon='settings')
        stop_btn = ui.button('强制停止', color='negative', icon='stop').props('disable=true')

    # --- Steps (auto from _STEP_CLASSES) ---

    step_params: dict[str, dict[str, object]] = {}
    step_cards: dict[str, ui.button] = {}

    import inspect

    def create_param_input(param_name: str, param: inspect.Parameter):
        default_value = param.default if param.default != inspect._empty else None
        param_type = param.annotation if param.annotation != inspect._empty else type(default_value)

        # number (float or int)
        if param_type in (float, int) or isinstance(default_value, (int, float)):
            fmt = '%.3f' if isinstance(default_value, float) else '%.0f'
            return ui.number(label=param_name, value=default_value, format=fmt).props('dense outlined size=sm').classes('w-36 min-w-36')
        # bool
        if param_type is bool or isinstance(default_value, bool):
            return ui.checkbox(text=param_name, value=bool(default_value or False)).props('dense')
        # fallback: string
        return ui.input(label=param_name, value='' if default_value is None else str(default_value)).props('dense outlined size=sm').classes('w-48 min-w-48')

    def render_step_card(step_name: str):
        """单行平铺：左=名称，中=参数，右=运行按钮"""
        import inspect
        from tasks.run_tasks import _STEP_CLASSES  # 使用已存在的步骤映射

        step_class = _STEP_CLASSES[step_name]
        sig = inspect.signature(step_class.__init__)

        with ui.card().classes('w-full mb-2 hover:shadow transition-all'):
            with ui.card_section().classes('p-3'):
                # 整行：左(名称) - 中(参数) - 右(运行)
                with ui.row().classes('items-center w-full gap-3 no-wrap'):
                    # 左：名称
                    ui.label(step_name).classes(
                        'font-bold text-base text-blue-700 shrink-0 min-w-40 max-w-64 truncate'
                    )

                    # 中：参数（单行横向，可滚动）
                    params_row = ui.row().classes(
                        'items-center gap-2 no-wrap overflow-x-auto flex-1'
                    )
                    with params_row:
                        step_params[step_name] = {}
                        for param_name, param in sig.parameters.items():
                            if param_name == 'self':
                                continue
                            # 复用你现有的输入工厂：create_param_input(param_name, param)
                            w = create_param_input(param_name, param)
                            step_params[step_name][param_name] = w

                    # 右：运行按钮
                    with ui.row().classes('items-center justify-end shrink-0'):
                        btn = ui.button('运行', color='primary', icon='play_arrow').classes('text-sm px-3')
                        step_cards[step_name] = btn
                        btn.on('click', lambda e, n=step_name: _on_run_step_click(n))
 
    # Render all steps (tiled)
    with ui.expansion('单步骤调试', icon='list_alt', value=True).classes('w-full mt-2'):
        ui.label('每个步骤可自定义参数；修改后点击“运行”').classes('text-sm text-gray-600 mb-2')
        with ui.grid(columns=1).classes('w-full gap-2 items-stretch'):
            for step_name in _STEP_CLASSES.keys():
                render_step_card(step_name)

    # --- Custom full process (single clean block) ---
    ui.separator().classes('my-3')
    ui.label('全流程控制').classes('text-md font-bold text-blue-600')

    # Auto-group steps by prefix: Step1*, Step2*, Step3*
    def group_steps(prefix: str):
        return sorted([s for s in _STEP_CLASSES.keys() if s.startswith(prefix)])

    with ui.expansion('自定义流程配置', icon='tune').classes('w-full mt-1') as full_config:
        full_config.value = False
        with ui.column().classes('gap-2 p-2'):
            step1_select = ui.select(group_steps('Step1'), multiple=True, value=group_steps('Step1'), label='Step1组 (只执行一次)').classes('mb-1')
            step2_select = ui.select(group_steps('Step2'), multiple=True, value=group_steps('Step2'), label='Step2组 (循环执行)').classes('mb-1')
            step3_select = ui.select(group_steps('Step3'), multiple=True, value=group_steps('Step3'), label='Step3组 (循环执行)').classes('mb-1')
            max_cycles_input = ui.number('最大循环次数', value=10, min=1, max=100).classes('w-32')

    # --- Handlers ---
    def _on_run_step_click(step_name: str):
        if is_task_running():
            ui.notify('已有任务在运行中，请先停止当前任务', type='warning')
            return
        # collect params
        kwargs = {}
        for pname, widget in step_params.get(step_name, {}).items():
            if hasattr(widget, 'value'):
                val = widget.value
                if val is not None and val != '':
                    kwargs[pname] = val
        try:
            logger.info(f'开始运行步骤: {step_name}, 参数: {kwargs}')
            start_step_thread(step_name, **kwargs)
            ui.notify(f'{step_name} 已启动', type='positive')
            step_cards[step_name].props('loading')
            stop_btn.props('disable=false')
        except Exception as e:
            logger.error(f'启动步骤失败: {e}')
            ui.notify(f'启动失败: {e}', type='negative')

    def _on_stop_click():
        if not is_task_running():
            ui.notify('当前没有正在运行的任务', type='info')
            return
        ui.notify('正在强制停止任务并清理...', type='warning', timeout=3000)
        try:
            force_stop_current_task()
            ui.notify('任务已停止', type='positive')
        except Exception as e:
            logger.error(f'强制停止异常: {e}')
            ui.notify(f'强制停止异常: {e}', type='negative')
        finally:
            for _, btn in step_cards.items():
                btn.props('loading=false')
            run_full_btn.props('loading=false')
            run_full_custom_btn.props('loading=false')
            stop_btn.props('disable=true')

    def _on_run_full_click():
        if is_task_running():
            ui.notify('已有任务在运行中，请先停止当前任务', type='warning')
            return
        try:
            logger.info('开始运行默认完整流程')
            start_default_full_process_thread()
            ui.notify('默认完整流程已启动', type='positive')
            run_full_btn.props('loading')
            stop_btn.props('disable=false')
        except Exception as e:
            logger.error(f'启动默认完整流程失败: {e}')
            ui.notify(f'启动失败: {e}', type='negative')

    def _on_run_full_custom_click():
        if is_task_running():
            ui.notify('已有任务在运行中，请先停止当前任务', type='warning')
            return
        s1 = step1_select.value or []
        s2 = step2_select.value or []
        s3 = step3_select.value or []
        max_cycles = int(max_cycles_input.value or 10)
        if not s1 and not s2 and not s3:
            ui.notify('请至少选择一个步骤组', type='warning')
            return
        try:
            logger.info(f'开始自定义完整流程: Step1={s1}, Step2={s2}, Step3={s3}, 最大循环={max_cycles}')
            start_full_process_thread()
            ui.notify('自定义完整流程已启动', type='positive')
            run_full_custom_btn.props('loading')
            stop_btn.props('disable=false')
        except Exception as e:
            logger.error(f'启动自定义完整流程失败: {e}')
            ui.notify(f'启动失败: {e}', type='negative')

    # wire buttons
    stop_btn.on('click', lambda e: _on_stop_click())
    run_full_btn.on('click', lambda e: _on_run_full_click())
    run_full_custom_btn.on('click', lambda e: _on_run_full_custom_click())


# -----------------------------------------------------------------------------
# Debug Panel (simplified)
# -----------------------------------------------------------------------------

def render_debug_panel():
    ui.markdown('## 诊断')

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
