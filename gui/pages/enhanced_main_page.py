from nicegui import ui
from core.logger import logger
from typing import Optional
from operations.executor.task_executor import (
    start_task_process_thread,
    stop as stop_task_process,
    is_task_process_running,
)
from operations.nodes import _TASK_NODE_CLASSES, _COND_NODE_CLASSES

from operations.debug_vars_enhanced import (
    get_enhanced_vars,
    get_enhanced_images,
    get_debug_summary,
    DebugLevel,
    DebugCategory,
)

from gui.utils import get_empty_img, prepare_image_for_display

# 配置
from core.config.operation_config import (
    load_operation_config,
    save_operation_config,
    OperationNodeConfig,
)

import threading
import inspect
import json


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
# Tasks Panel (refactored; per-parameter inputs instead of kwargs)
# -----------------------------------------------------------------------------

def render_tasks_panel():
    ui.markdown('## 控制面板')

    cfg = load_operation_config()

    # UI 内存态：仅编辑 task/condition；target 在保存时按 condition 的 id 自动生成
    def _cfg_nodes_to_state():
        """把配置里的 nodes 还原为 UI 可编辑的状态列表：保留 task / condition / target"""
        items = getattr(cfg, 'nodes', []) or []
        out = []
        for n in items:
            n_type = getattr(n, 'type', None)
            n_id = getattr(n, 'id', '')
            n_name = getattr(n, 'name', '')
            n_params = getattr(n, 'parameters', {}) or {}

            if n_type == 'task':
                out.append({'type': 'task', 'name': n_name, 'parameters': dict(n_params)})

            elif n_type == 'condition':
                out.append({'type': 'condition', 'id': n_id, 'name': n_name, 'parameters': dict(n_params)})

            elif n_type == 'target':
                # target 也加入状态，这样 _render_items() 的 'target' 分支能渲染出来
                out.append({'type': 'target', 'id': n_id, 'name': n_name})

            else:
                # 未知类型忽略或记录
                pass
        return out

    nodes_state = _cfg_nodes_to_state()

    # ---------- 单步运行（逐参数输入） ----------
    step_param_widgets: dict[str, dict[str, ui.element]] = {}
    step_cards: dict[str, ui.button] = {}
    _single_task_thread: list[Optional[threading.Thread]] = [None]

    def _create_param_input(param_name: str, param: inspect.Parameter, preset=None) -> ui.element:
        """根据参数类型/默认值渲染控件（逐个参数）"""
        default = param.default if param.default is not inspect._empty else None
        annot = param.annotation if param.annotation is not inspect._empty else type(default)
        init_val = preset if preset is not None else default

        # number
        if annot in (int, float) or isinstance(init_val, (int, float)):
            fmt = '%.3f' if (isinstance(init_val, float) or annot is float) else '%.0f'
            return ui.number(label=param_name, value=init_val, format=fmt).props('dense outlined size=sm').classes('w-36 min-w-36')
        # bool
        if annot is bool or isinstance(init_val, bool):
            return ui.checkbox(text=param_name, value=bool(init_val or False)).props('dense')
        # dict / list → JSON 输入
        if annot in (dict, list) or isinstance(init_val, (dict, list)):
            text = json.dumps(init_val or ({} if annot is dict else []), ensure_ascii=False)
            return ui.textarea(label=param_name, value=text).props('dense outlined autogrow').classes('w-80 min-w-80')
        # 其余一律字符串
        return ui.input(label=param_name, value='' if init_val is None else str(init_val)).props('dense outlined size=sm').classes('w-56 min-w-56')

    def _read_param_widget(widget: ui.element, desired_annot, default_val):
        """从控件读值并做基本类型转换"""
        val = getattr(widget, 'value', None)
        if val is None or val == '':
            return None
        try:
            if desired_annot is int:
                return int(val)
            if desired_annot is float:
                return float(val)
            if desired_annot is bool:
                return bool(val)
            if desired_annot in (dict, list):
                return json.loads(val) if isinstance(val, str) else val
            # fallback: 原样/字符串
            return val
        except Exception:
            # 转换失败就退回默认值
            return default_val

    def _preset_for_step(step_name: str) -> dict:
        for item in nodes_state:
            if item.get('type') == 'task' and item.get('name') == step_name:
                return dict(item.get('parameters') or {})
        return {}

    def _start_single_task_thread(step_name: str, param_values: dict):
        if _single_task_thread[0] and _single_task_thread[0].is_alive():
            logger.warning('已有单步任务在运行中')
            return
        if is_task_process_running():
            logger.warning('主流程正在运行，无法单步调试')
            return
        task_cls = _TASK_NODE_CLASSES.get(step_name)
        if not task_cls:
            logger.error(f'未知步骤类: {step_name}')
            return

        def _worker():
            try:
                logger.info(f'[single-step] {step_name} params={param_values}')
                task_cls(**param_values).run()
            except Exception as e:
                logger.error(f'[single-step] 执行 {step_name} 异常: {e}')

        t = threading.Thread(target=_worker, daemon=True)
        _single_task_thread[0] = t
        t.start()

    def _render_single_task_card(step_name: str):
        step_class = _TASK_NODE_CLASSES[step_name]
        sig = inspect.signature(step_class.__init__)
        preset = _preset_for_step(step_name)

        def _on_click_run(n=step_name):
            if is_task_process_running():
                logger.warning('主流程正在运行，请先停止')
                return
            # 逐个参数读取（无参数则为空 dict）
            param_values = {}
            for pname, param in ((pn, pa) for pn, pa in sig.parameters.items() if pn != 'self'):
                widget = step_param_widgets.get(step_name, {}).get(pname)
                if not widget:
                    continue
                default = param.default if param.default is not inspect._empty else None
                annot = param.annotation if param.annotation is not inspect._empty else type(default)
                v = _read_param_widget(widget, annot, default)
                if v is not None:
                    param_values[pname] = v
            _start_single_task_thread(n, param_values)
            step_cards[n].props('loading')

        with ui.card().classes('w-full mb-2 hover:shadow transition-all'):
            with ui.card_section().classes('p-3'):
                with ui.row().classes('items-center w-full gap-3 no-wrap'):
                    ui.label(step_name).classes(
                        'font-bold text-base text-blue-700 shrink-0 min-w-40 max-w-64 truncate'
                    )

                    # 仅当存在除 self 外的参数时渲染参数区域
                    step_param_widgets[step_name] = {}
                    _param_items = [(pn, pa) for pn, pa in sig.parameters.items() if pn != 'self']
                    if _param_items:
                        params_col = ui.column().classes('gap-2 flex-1')
                        with params_col:
                            for pname, param in _param_items:
                                w = _create_param_input(pname, param, preset.get(pname))
                                step_param_widgets[step_name][pname] = w

                    # 运行按钮
                    with ui.row().classes('items-center justify-end shrink-0'):
                        btn = ui.button('运行', color='primary', icon='play_arrow').classes('text-sm px-3')
                        step_cards[step_name] = btn
                        btn.on('click', _on_click_run)

    with ui.expansion('单步骤调试', icon='list_alt', value=True).classes('w-full mt-2'):
        ui.label('每个步骤可自定义参数；修改后点击“运行”').classes('text-sm text-gray-600 mb-2')
        with ui.grid(columns=1).classes('w-full gap-2 items-stretch'):
            for _step_name in _TASK_NODE_CLASSES.keys():
                _render_single_task_card(_step_name)
    # ---------- 顺序配置（task / condition；target 自动生成） ----------
    ui.separator().classes('my-3')
    ui.label('任务配置（顺序与参数）').classes('text-md font-bold text-blue-600')
    ui.label('条件节点返回 False 时跳到“同 id 的 target”（保存时自动生成）').classes('text-sm text-gray-600 mb-2')

    items_container = ui.column().classes('w-full gap-2')
    task_choices = list(_TASK_NODE_CLASSES.keys())
    cond_choices = list(_COND_NODE_CLASSES.keys())

    def _render_items():
        items_container.clear()
        for idx, item in enumerate(nodes_state):
            with items_container:
                with ui.card().classes('w-full mb-2 hover:shadow transition-all'):
                    with ui.card_section().classes('p-3'):
                        with ui.row().classes('items-center w-full gap-3 no-wrap'):
                            ui.badge(str(idx + 1)).classes('shrink-0 text-base font-bold')
                            itype = item.get('type', 'task')

                            if itype == 'task':
                                # 任务节点：选择类名 + 按签名逐参数渲染
                                sel = ui.select(
                                    task_choices,
                                    value=item['name'],
                                    label='任务类',
                                    clearable=False,
                                    on_change=lambda e: on_step_change(e.value)
                                ).props('dense outlined').classes('w-56 shrink-0')

                                def on_step_change(new_value, i=idx):
                                    if i < len(nodes_state):
                                        # 获取更新后的值 (改进的值获取逻辑)
                                        if new_value is not None and new_value in task_choices:
                                            nodes_state[i]['name'] = new_value
                                            nodes_state[i]['parameters'] = {}
                                        else:
                                            pass  # 无法获取有效的任务节点名称，跳过更新
                                        _render_items()

                                param_widgets = {}
                                step_name = item.get('name')
                                if step_name and step_name in _TASK_NODE_CLASSES:
                                    sig = inspect.signature(_TASK_NODE_CLASSES[step_name].__init__)
                                    # 仅当存在除 self 外的参数才渲染参数区域
                                    _param_items = [(pn, pa) for pn, pa in sig.parameters.items() if pn != 'self']
                                    if _param_items:
                                        with ui.column().classes('gap-2 flex-1 mt-2'):
                                            for pname, p in _param_items:
                                                current = (item.get('parameters') or {}).get(pname)
                                                w = _create_param_input(pname, p, preset=current)
                                                param_widgets[pname] = w

                                # 控制按钮
                                with ui.row().classes('items-center justify-end shrink-0 gap-1'):
                                    ui.button(icon='arrow_upward',
                                            on_click=lambda e, i=idx: (_move_up(i), _render_items()))\
                                    .props('dense flat size=sm').classes('text-xs')
                                    ui.button(icon='arrow_downward',
                                            on_click=lambda e, i=idx: (_move_down(i), _render_items()))\
                                    .props('dense flat size=sm').classes('text-xs')
                                    ui.button(icon='delete', color='negative',
                                            on_click=lambda e, i=idx: (_delete(i), _render_items()))\
                                    .props('dense flat size=sm').classes('text-xs')

                                item['__param_widgets'] = param_widgets
                                item['__sel'] = sel

                            elif itype == 'condition':
                                # 条件节点：需要显式 id（用于与 target 同 id 跳转）
                                
                                sel = ui.select(
                                    cond_choices,
                                    value=item.get('name'),
                                    label='条件类',
                                    clearable=False,
                                    on_change=lambda e: on_cond_change(e.value)
                                ).props('dense outlined').classes('w-56 shrink-0')
                                
                                id_in = ui.input(
                                    '节点 ID（与 target 同 id）',
                                    value=item.get('id', '')
                                ).props('dense outlined size=sm').classes('w-56')

                                def on_cond_change(new_value, i=idx):
                                    if i < len(nodes_state):
                                        if new_value is not None and new_value in cond_choices:
                                            nodes_state[i]['name'] = new_value
                                            nodes_state[i]['parameters'] = {}
                                        else:
                                            pass  # 无法获取有效的条件节点名称，跳过更新
                                        _render_items()

                                param_widgets = {}
                                cond_name = item.get('name')
                                if cond_name and cond_name in _COND_NODE_CLASSES:
                                    sig = inspect.signature(_COND_NODE_CLASSES[cond_name].__init__)
                                    _param_items = [(pn, pa) for pn, pa in sig.parameters.items() if pn != 'self']
                                    if _param_items:
                                        with ui.column().classes('gap-2 flex-1 mt-2'):
                                            for pname, p in _param_items:
                                                current = (item.get('parameters') or {}).get(pname)
                                                w = _create_param_input(pname, p, preset=current)
                                                param_widgets[pname] = w

                                # 控制按钮
                                with ui.row().classes('items-center justify-end shrink-0 gap-1'):
                                    ui.button(icon='arrow_upward',
                                            on_click=lambda e, i=idx: (_move_up(i), _render_items()))\
                                    .props('dense flat size=sm').classes('text-xs')
                                    ui.button(icon='arrow_downward',
                                            on_click=lambda e, i=idx: (_move_down(i), _render_items()))\
                                    .props('dense flat size=sm').classes('text-xs')
                                    ui.button(icon='delete', color='negative',
                                            on_click=lambda e, i=idx: (_delete(i), _render_items()))\
                                    .props('dense flat size=sm').classes('text-xs')

                                item['__id_input'] = id_in
                                item['__param_widgets'] = param_widgets
                                item['__sel'] = sel

                            elif itype == 'target':
                                # Target 节点：用于 condition=False 的跳转锚点（与 condition 同 ID）
                                ui.label('Target 节点').classes('font-bold text-emerald-700 shrink-0 min-w-28')

                                # ID 建议只读，避免与 condition 脱钩；如需允许修改，去掉 readonly
                                id_in = ui.input(
                                    '目标 ID（应等于对应条件的 ID）',
                                    value=item.get('id', '')
                                ).props('dense outlined size=sm readonly').classes('w-56')

                                # target 一般无参数，不渲染参数区

                                # 控制按钮
                                with ui.row().classes('items-center justify-end shrink-0 gap-1'):
                                    ui.button(icon='arrow_upward',
                                            on_click=lambda e, i=idx: (_move_up(i), _render_items()))\
                                    .props('dense flat size=sm').classes('text-xs')
                                    ui.button(icon='arrow_downward',
                                            on_click=lambda e, i=idx: (_move_down(i), _render_items()))\
                                    .props('dense flat size=sm').classes('text-xs')
                                    ui.button(icon='delete', color='negative',
                                            on_click=lambda e, i=idx: (_delete(i), _render_items()))\
                                    .props('dense flat size=sm').classes('text-xs')

                                # 供保存时读取（若你在保存逻辑里需要）
                                item['__id_input_target'] = id_in

                            else:
                                # 未知类型占位
                                ui.label(f'未知节点类型: {itype}').classes('text-red-600')


    def _move_up(i): 
        if i > 0: nodes_state[i-1], nodes_state[i] = nodes_state[i], nodes_state[i-1]

    def _move_down(i):
        if i < len(nodes_state) - 1: nodes_state[i+1], nodes_state[i] = nodes_state[i], nodes_state[i+1]

    def _delete(i):
        nodes_state.pop(i)

    def _add_task_item():
        nodes_state.append({'type': 'task', 'name': (next(iter(_TASK_NODE_CLASSES.keys()), '') if _TASK_NODE_CLASSES else ''), 'parameters': {}})
        _render_items()

    def _add_condition_item():
        next_idx = len([x for x in nodes_state if x.get('type') == 'condition']) + 1
        nodes_state.append({'type': 'condition', 'id': f'cond_{next_idx}', 'name': (next(iter(_COND_NODE_CLASSES.keys()), '') if _COND_NODE_CLASSES else ''), 'parameters': {}})
        _render_items()

    def _save_items():
        """从 UI 读回 -> 保存到 cfg.nodes；
        - 显式出现在 UI 的 target 节点按其位置保存
        - 若有 condition 没有对应 target，则在末尾自动补一个
        """
        new_nodes: list[OperationNodeConfig] = []
        cond_ids: list[str] = []
        target_ids: list[str] = []

        for idx, item in enumerate(nodes_state, start=1):
            itype = item.get('type', 'task')

            if itype == 'task':
                name = getattr(item.get('__sel'), 'value', item.get('name')) if item.get('__sel') else item.get('name')
                params = {}
                step_name = name
                if step_name and step_name in _TASK_NODE_CLASSES:
                    sig = inspect.signature(_TASK_NODE_CLASSES[step_name].__init__)
                    for pname, p in sig.parameters.items():
                        if pname == 'self':
                            continue
                        widget = (item.get('__param_widgets') or {}).get(pname)
                        if not widget:
                            continue
                        default = p.default if p.default is not inspect._empty else None
                        annot = p.annotation if p.annotation is not inspect._empty else type(default)
                        v = _read_param_widget(widget, annot, default)
                        if v is not None:
                            params[pname] = v
                new_nodes.append(OperationNodeConfig(type='task', id=f'task_{idx}', name=name, parameters=params))

            elif itype == 'condition':
                node_id = getattr(item.get('__id_input'), 'value', item.get('id')) if item.get('__id_input') else item.get('id') or f'cond_{idx}'
                cond_name = getattr(item.get('__sel'), 'value', item.get('name')) if item.get('__sel') else item.get('name')
                params = {}
                if cond_name and cond_name in _COND_NODE_CLASSES:
                    sig = inspect.signature(_COND_NODE_CLASSES[cond_name].__init__)
                    for pname, p in sig.parameters.items():
                        if pname == 'self':
                            continue
                        widget = (item.get('__param_widgets') or {}).get(pname)
                        if not widget:
                            continue
                        default = p.default if p.default is not inspect._empty else None
                        annot = p.annotation if p.annotation is not inspect._empty else type(default)
                        v = _read_param_widget(widget, annot, default)
                        if v is not None:
                            params[pname] = v

                new_nodes.append(OperationNodeConfig(type='condition', id=node_id, name=cond_name, parameters=params))
                cond_ids.append(node_id)

            elif itype == 'target':
                # 显式保存 target（使用 UI 中的只读/可编辑输入）
                t_id = getattr(item.get('__id_input_target'), 'value', item.get('id', '')) if item.get('__id_input_target') else item.get('id', '')
                t_name = getattr(item.get('__name_input_target'), 'value', item.get('name', 'TargetAnchor')) if item.get('__name_input_target') else item.get('name', 'TargetAnchor')
                new_nodes.append(OperationNodeConfig(type='target', id=t_id, name=t_name, parameters={}))
                target_ids.append(t_id)

            # 其它类型忽略

        # 自动补齐：对没有显式 target 的 condition，追加一个默认 target
        missing = [cid for cid in cond_ids if cid not in set(target_ids)]
        for cid in missing:
            new_nodes.append(OperationNodeConfig(type='target', id=cid, name='TargetAnchor', parameters={}))

        try:
            cfg.nodes = new_nodes
            save_operation_config(cfg)
            if missing:
                logger.warning(f'配置已保存；为 {len(missing)} 个条件自动补充 target')
            else:
                logger.info('配置已保存')
        except Exception as e:
            logger.error(f'保存失败: {e}')

    with ui.row().classes('gap-2 mt-1'):
        ui.button('新增任务节点', icon='add', on_click=_add_task_item).props('dense')
        ui.button('新增条件节点', icon='add_alert', on_click=_add_condition_item).props('dense')
        ui.button('保存配置', color='primary', icon='save', on_click=_save_items).props('dense')

    # 初次渲染
    if not nodes_state:
        nodes_state.append({'type': 'task', 'name': next(iter(_TASK_NODE_CLASSES.keys()), ''), 'parameters': {}})
    _render_items()

    # 运行/停止（新执行器）
    def _update_button_states():
        running = is_task_process_running()
        for btn in step_cards.values():
            btn.props('loading' if running else 'loading=false')
        run_full_btn.props('loading' if running else 'loading=false')
        stop_btn.props('disable=false' if running else 'disable=true')

    def _on_run_config_sequence_click():
        if is_task_process_running():
            logger.warning('已有任务在运行中')
            return
        nodes_count = len(getattr(cfg, 'nodes', []) or [])
        if nodes_count == 0:
            logger.warning('没有配置任何节点，请先添加并保存')
            return
        try:
            logger.info(f'开始运行流程，共 {nodes_count} 个节点')
            start_task_process_thread()
            logger.info(f'流程已启动（{nodes_count} 节点）')
            _update_button_states()
        except Exception as e:
            logger.error(f'启动失败: {e}')

    def _on_stop_click():
        if not is_task_process_running():
            logger.info('当前没有正在运行的流程')
            return
        logger.info('用户请求停止流程')
        stop_task_process()
        logger.warning('已请求停止，将在下一节点前停下')
        _update_button_states()

    with ui.row().classes('gap-2 w-full'):
        run_full_btn = ui.button('运行配置顺序', color='secondary', icon='play_arrow')
        run_full_btn.on('click', _on_run_config_sequence_click)

        stop_btn = ui.button('停止', color='negative', icon='stop').props('disable=true')
        stop_btn.on('click', _on_stop_click)

    ui.timer(1.0, _update_button_states)


# -----------------------------------------------------------------------------
# Debug Panel (simplified)
# -----------------------------------------------------------------------------

def render_debug_panel():
    ui.markdown('## 调试参数')

    with ui.card().classes('w-full mb-3'):
        with ui.row().classes('flex-wrap gap-2 p-2'):
            empty_img = get_empty_img()
            img1 = ui.interactive_image(empty_img).classes('rounded-borders')
            img2 = ui.interactive_image(empty_img).classes('rounded-borders')

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
        _ = get_debug_summary()

        items = list(images_data.items())[:2]
        try:
            if len(items) > 0:
                img1.set_source(prepare_image_for_display(items[0][1].image))
            if len(items) > 1:
                img2.set_source(prepare_image_for_display(items[1][1].image))
        except Exception as e:
            logger.warning(f'更新图像失败: {e}')

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
