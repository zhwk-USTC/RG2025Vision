from nicegui import ui
from core.logger import logger
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from functools import lru_cache
import threading
import inspect
import json
import copy

from operations.executor.task_executor import (
    start_task_process_thread,
    stop as stop_task_process,
    is_task_process_running,
)
from operations.nodes import _TASK_NODE_CLASSES, _COND_NODE_CLASSES

# 配置
from operations.config.operation_config import (
    get_current_operation,
    save_current_operation,
    add_operation,
    remove_operation,
    OperationNodeConfig,
    OperationConfig,
    set_current_operation,
    list_available_operations,
    get_operation_manager,
    save_operation_manager,
)

# ===============================
# 共享上下文
# ===============================
@dataclass
class UIPanelContext:
    nodes_state: List[dict]
    step_param_widgets: Dict[str, Dict[str, ui.element]] = field(default_factory=dict)
    step_cards: Dict[str, ui.button] = field(default_factory=dict)
    run_full_btn: Optional[ui.button] = None
    stop_btn: Optional[ui.button] = None


# ===============================
# 模块级工具函数（两块 UI 共用）
# ===============================
def _save_operation_mgr():
    save_operation_manager()


def _json_dump(obj, is_dict: bool):
    return json.dumps(obj or ({} if is_dict else []), ensure_ascii=False)


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
        return val
    except Exception:
        return default_val


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
        text = _json_dump(init_val, annot is dict)
        return ui.textarea(label=param_name, value=text).props('dense outlined autogrow').classes('w-80 min-w-80')
    # 其余一律字符串
    return ui.input(label=param_name, value='' if init_val is None else str(init_val)).props('dense outlined size=sm').classes('w-56 min-w-56')


def _cfg_nodes_to_state(cfg):
    """配置 -> UI 状态（task/condition/target/note/subflow）"""
    items = getattr(cfg, 'nodes', []) or []
    out = []
    for n in items:
        n_type = getattr(n, 'type', None)
        base = {'type': n_type, 'id': getattr(n, 'id', ''), 'name': getattr(n, 'name', '')}
        # 这里把 note 加进“有 parameters 的类型”
        if n_type in ('task', 'condition', 'note', 'subflow'):
            base['parameters'] = dict(getattr(n, 'parameters', {}) or {})
        # 这里把 note 加进可加入的类型列表
        if n_type in ('task', 'condition', 'target', 'note', 'subflow'):
            # 对于 subflow 节点，从 parameters 中提取 subflow_name 作为 name
            if n_type == 'subflow':
                subflow_name = (getattr(n, 'parameters', {}) or {}).get('subflow_name', '')
                base['name'] = subflow_name
            out.append(base)
    return out


# 参数签名缓存（去掉 self）
@lru_cache(maxsize=None)
def _ctor_params(cls):
    sig = inspect.signature(cls.__init__)
    return [(pn, pa) for pn, pa in sig.parameters.items() if pn != 'self']


def _param_default_annot(param: inspect.Parameter):
    default = param.default if param.default is not inspect._empty else None
    annot = param.annotation if param.annotation is not inspect._empty else type(default)
    return default, annot


# ===============================
# 单步调试面板（模块级）
# ===============================
def render_single_step_panel(ctx: UIPanelContext):
    """渲染单步骤调试面板"""
    _single_task_thread: list[Optional[threading.Thread]] = [None]

    def _preset_for_step(step_name: str) -> dict:
        for item in ctx.nodes_state:
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
                # 启动前运行 system_init
                init_cls = _TASK_NODE_CLASSES.get('system_init')
                if init_cls:
                    try:
                        init_cls().run()
                        logger.info('[single-step] system_init 执行完成')
                    except Exception as e:
                        logger.error(f'[single-step] system_init 执行异常: {e}')
                # 执行单个任务
                task_cls(**param_values).run()
                logger.info(f'[single-step] {step_name} 执行完成')
            except Exception as e:
                logger.error(f'[single-step] 执行 {step_name} 异常: {e}')
            finally:
                # 结束前运行 system_cleanup
                cleanup_cls = _TASK_NODE_CLASSES.get('system_cleanup')
                if cleanup_cls:
                    try:
                        cleanup_cls().run()
                        logger.info('[single-step] system_cleanup 执行完成')
                    except Exception as e:
                        logger.error(f'[single-step] system_cleanup 执行异常: {e}')

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
            param_values = {}
            for pname, param in ((pn, pa) for pn, pa in sig.parameters.items() if pn != 'self'):
                widget = ctx.step_param_widgets.get(step_name, {}).get(pname)
                if not widget:
                    continue
                default = param.default if param.default is not inspect._empty else None
                annot = param.annotation if param.annotation is not inspect._empty else type(default)
                v = _read_param_widget(widget, annot, default)
                if v is not None:
                    param_values[pname] = v
            _start_single_task_thread(n, param_values)
            if n in ctx.step_cards:
                ctx.step_cards[n].props('loading')

        with ui.expansion(step_name, value=False).classes('w-full mb-1').props('header-class="font-bold text-base text-blue-700"'):
            with ui.row().classes('items-start gap-3 w-full'):
                ctx.step_param_widgets[step_name] = {}
                _param_items = [(pn, pa) for pn, pa in sig.parameters.items() if pn != 'self']
                if _param_items:
                    with ui.column().classes('gap-2 flex-1'):
                        for pname, param in _param_items:
                            w = _create_param_input(pname, param, preset.get(pname))
                            ctx.step_param_widgets[step_name][pname] = w
                btn = ui.button('运行', color='primary', icon='play_arrow').classes('text-sm px-3')
                ctx.step_cards[step_name] = btn
                btn.on('click', _on_click_run)

    # with ui.expansion('单步骤调试', icon='list_alt', value=False).classes('w-full mt-2'):
    ui.label('每个步骤可自定义参数；修改后点击“运行”').classes('text-sm text-gray-600 mb-2')
    with ui.grid(columns=1).classes('w-full gap-2 items-stretch'):
        for _step_name in _TASK_NODE_CLASSES.keys():
            _render_single_task_card(_step_name)


# ===============================
# 流程管理/配置/运行 面板（模块级）
# ===============================
def render_flow_panel(ctx: UIPanelContext):
    """渲染流程区（管理 + 配置 + 运行）"""
    
    _flow_single_task_thread: list[Optional[threading.Thread]] = [None]

    def _start_flow_single_task_thread(idx: int):
        if _flow_single_task_thread[0] and _flow_single_task_thread[0].is_alive():
            logger.warning('已有流程单步任务在运行中')
            return
        if is_task_process_running():
            logger.warning('主流程正在运行，无法单步调试')
            return
        item = ctx.nodes_state[idx]
        if item.get('type') != 'task':
            logger.warning('只能运行任务节点')
            return
        task_name = item.get('name')
        if not task_name:
            logger.error('任务名称为空')
            return
        task_cls = _TASK_NODE_CLASSES.get(task_name)
        if not task_cls:
            logger.error(f'未知任务类: {task_name}')
            return

        # 获取参数
        param_values = {}
        if '__param_widgets' in item:
            for pname, param in _ctor_params(task_cls):
                w = item['__param_widgets'].get(pname)
                if not w:
                    continue
                d, a = _param_default_annot(param)
                v = _read_param_widget(w, a, d)
                if v is not None:
                    param_values[pname] = v

        def _worker():
            try:
                logger.info(f'[flow-single-step] {task_name} params={param_values}')
                # 启动前运行 system_init
                init_cls = _TASK_NODE_CLASSES.get('system_init')
                if init_cls:
                    try:
                        init_cls().run()
                        logger.info('[flow-single-step] system_init 执行完成')
                    except Exception as e:
                        logger.error(f'[flow-single-step] system_init 执行异常: {e}')
                # 执行单个任务
                task_cls(**param_values).run()
                logger.info(f'[flow-single-step] {task_name} 执行完成')
            except Exception as e:
                logger.error(f'[flow-single-step] 执行 {task_name} 异常: {e}')
            finally:
                # 结束前运行 system_cleanup
                cleanup_cls = _TASK_NODE_CLASSES.get('system_cleanup')
                if cleanup_cls:
                    try:
                        cleanup_cls().run()
                        logger.info('[flow-single-step] system_cleanup 执行完成')
                    except Exception as e:
                        logger.error(f'[flow-single-step] system_cleanup 执行异常: {e}')

        t = threading.Thread(target=_worker, daemon=True)
        _flow_single_task_thread[0] = t
        t.start()
    
    # === 颜色与样式常量（放在 render_flow_panel(ctx) 内，三函数上方）===
    STYLE = {
        'task':    {'border': 'border-blue-500',    'icon': 'play_arrow',   'icon_cls': 'text-blue-600',    'title_cls': 'text-blue-700'},
        'cond':    {'border': 'border-amber-500',   'icon': 'rule',         'icon_cls': 'text-amber-600',   'title_cls': 'text-amber-700'},
        'target':  {'border': 'border-emerald-500', 'icon': 'flag',         'icon_cls': 'text-emerald-600', 'title_cls': 'text-emerald-700'},
        'note': {'border': 'border-violet-500', 'icon': 'sticky_note_2', 'icon_cls': 'text-violet-600', 'title_cls': 'text-violet-700'},
        'subflow': {'border': 'border-orange-500', 'icon': 'call_split',   'icon_cls': 'text-orange-600', 'title_cls': 'text-orange-700'},
    }

    def _card_classes(kind: str) -> str:
        """统一卡片样式：左侧竖条 + 淡灰背景 + 悬浮阴影"""
        return f"w-full mb-2 transition-all bg-gray-50 hover:shadow border-l-4 {STYLE[kind]['border']}"

    def _title_label(text: str, kind: str):
        return ui.label(text).classes(f"font-bold text-base shrink-0 {STYLE[kind]['title_cls']}")

    def _count_target_refs(tid: str) -> int:
        """统计有多少 condition 节点引用了该 target id"""
        if not tid:
            return 0
        return sum(1 for it in ctx.nodes_state if it.get('type') == 'condition' and it.get('id') == tid)

    # ---------- 流程管理 UI ----------
    ui.separator().classes('my-3')
    ui.label('工作流程管理').classes('text-md font-bold text-green-600')

    # 当前流程名称（用于默认选中）
    current_operation_state = {'value': ''}

    def refresh_current_operation():
        """确保至少有一个默认流程，并同步当前流程名称"""
        available_ops = list_available_operations()
        if not available_ops:
            default_config = OperationConfig(name="默认流程", description="系统默认工作流程")
            add_operation("默认流程", default_config)
            set_current_operation("默认流程")
            _save_operation_mgr()
            logger.info("已创建默认工作流程")
        cur = get_current_operation()
        current_operation_state['value'] = cur.name

    refresh_current_operation()

    # --- 顶部行：选择/新建/删除/复制 ---
    with ui.row().classes('items-center gap-3 mb-3'):
        available_ops = list_available_operations()
        default_value = current_operation_state['value'] if current_operation_state['value'] in available_ops else (available_ops[0] if available_ops else None)

        def refresh_operation_select():
            """刷新操作选择下拉框"""
            ops = list_available_operations()
            operation_select.set_options(ops)
            current_cfg = get_current_operation()
            if current_cfg.name in ops:
                operation_select.set_value(current_cfg.name)
            elif ops:
                operation_select.set_value(ops[0])
                set_current_operation(ops[0])
            else:
                operation_select.set_value(None)

        # current_info_container = ui.row().classes('mb-3 p-2 bg-blue-50 rounded')

        def refresh_operation_info():
            """刷新流程信息显示"""
            pass
            # current_info_container.clear()
            # with current_info_container:
            #     cur = get_current_operation()
            #     ui.icon('info').classes('text-blue-600')
            #     ui.label(f'当前流程: {cur.name}').classes('font-medium text-blue-800')
            #     if cur.description:
            #         ui.label(f'描述: {cur.description}').classes('text-sm text-blue-600 ml-2')
            #     nodes_count = len(getattr(cur, 'nodes', []) or [])
            #     ui.label(f'节点数: {nodes_count}').classes('text-sm text-blue-600 ml-2')

        def refresh_operation_config():
            """刷新整个操作配置（并重渲流程配置区）"""
            cfg = get_current_operation()
            ctx.nodes_state[:] = _cfg_nodes_to_state(cfg)
            refresh_operation_info()
            refresh_operation_select()
            _save_operation_mgr()
            _render_items()

        def on_operation_change(new_value):
            """切换工作流程"""
            ops = list_available_operations()
            if new_value and new_value in ops and set_current_operation(new_value):
                current_operation_state['value'] = new_value
                refresh_operation_config()
                logger.info(f'已切换到工作流程: {new_value}')
            elif new_value:
                logger.warning(f'切换工作流程失败: {new_value}')

        operation_select = ui.select(
            available_ops,
            value=default_value,
            label='选择工作流程',
            on_change=lambda e: on_operation_change(e.value)
        ).props('dense outlined').classes('w-64')

        def show_create_operation_dialog():
            with ui.dialog() as dialog, ui.card():
                with ui.card_section():
                    ui.label('创建新工作流程').classes('text-lg font-bold')
                with ui.card_section():
                    name_input = ui.input('流程名称', placeholder='请输入流程名称').props('dense outlined').classes('w-full')
                    desc_input = ui.textarea('流程描述', placeholder='请输入流程描述（可选）').props('dense outlined').classes('w-full')
                with ui.card_actions().classes('justify-end'):
                    ui.button('取消', on_click=dialog.close).props('flat')
                    ui.button('创建', color='primary',
                              on_click=lambda: create_new_operation(name_input.value, desc_input.value, dialog)).props('unelevated')
            dialog.open()

        def create_new_operation(name: str, description: str, dialog):
            if not name or not name.strip():
                logger.warning('流程名称不能为空')
                return
            if name in list_available_operations():
                logger.warning(f'流程名称 "{name}" 已存在')
                return
            try:
                new_config = OperationConfig(name=name, description=(description or '').strip())
                add_operation(name, new_config)
                set_current_operation(name)
                get_operation_manager()
                _save_operation_mgr()
                refresh_operation_config()
                logger.info(f'成功创建工作流程: {name}')
                dialog.close()
            except Exception as e:
                logger.error(f'创建工作流程失败: {e}')

        def delete_current_operation():
            cur = get_current_operation()
            if cur.name in ("无可用工作流程", "无效工作流程"):
                logger.warning('无有效流程可删除')
                return
            if len(list_available_operations()) <= 1:
                logger.warning('至少需要保留一个工作流程')
                return
            with ui.dialog() as dialog, ui.card():
                with ui.card_section():
                    ui.label('确认删除').classes('text-lg font-bold text-red-600')
                    ui.label(f'确定要删除工作流程 "{cur.name}" 吗？此操作不可撤销。')
                with ui.card_actions().classes('justify-end'):
                    ui.button('取消', on_click=dialog.close).props('flat')
                    ui.button('删除', color='negative',
                              on_click=lambda: confirm_delete_operation(cur.name, dialog)).props('unelevated')
            dialog.open()

        def confirm_delete_operation(name: str, dialog):
            try:
                if remove_operation(name):
                    _save_operation_mgr()
                    refresh_operation_config()
                    logger.info(f'已删除工作流程: {name}')
                else:
                    logger.error(f'删除工作流程失败: {name}')
                dialog.close()
            except Exception as e:
                logger.error(f'删除工作流程异常: {e}')
                dialog.close()

        def show_copy_operation_dialog():
            cur = get_current_operation()
            if cur.name in ("无可用工作流程", "无效工作流程"):
                logger.warning('无有效流程可复制')
                return
            with ui.dialog() as dialog, ui.card():
                with ui.card_section():
                    ui.label('复制工作流程').classes('text-lg font-bold')
                    ui.label(f'复制来源: {cur.name}')
                with ui.card_section():
                    new_name_input = ui.input('新流程名称', placeholder='请输入新流程名称').props('dense outlined').classes('w-full')
                    new_desc_input = ui.textarea('流程描述', value=cur.description,
                                                 placeholder='请输入流程描述（可选）').props('dense outlined').classes('w-full')
                with ui.card_actions().classes('justify-end'):
                    ui.button('取消', on_click=dialog.close).props('flat')
                    ui.button('复制', color='primary',
                              on_click=lambda: copy_current_operation(cur, new_name_input.value, new_desc_input.value, dialog)
                              ).props('unelevated')
            dialog.open()

        def copy_current_operation(source_config: OperationConfig, new_name: str, new_description: str, dialog):
            if not new_name or not new_name.strip():
                logger.warning('新流程名称不能为空')
                return
            if new_name in list_available_operations():
                logger.warning(f'流程名称 "{new_name}" 已存在')
                return
            try:
                new_config = copy.deepcopy(source_config)
                new_config.name = new_name
                new_config.description = (new_description or '').strip()
                add_operation(new_name, new_config)
                set_current_operation(new_name)
                _save_operation_mgr()
                refresh_operation_config()
                logger.info(f'成功复制工作流程: {new_name}')
                dialog.close()
            except Exception as e:
                logger.error(f'复制工作流程失败: {e}')

        def show_rename_operation_dialog():
            cur = get_current_operation()
            if cur.name in ("无可用工作流程", "无效工作流程"):
                logger.warning('无有效流程可重命名')
                return
            with ui.dialog() as dialog, ui.card():
                with ui.card_section():
                    ui.label('重命名工作流程').classes('text-lg font-bold')
                    ui.label(f'当前名称: {cur.name}')
                with ui.card_section():
                    new_name_input = ui.input('新流程名称', placeholder='请输入新流程名称').props('dense outlined').classes('w-full')
                with ui.card_actions().classes('justify-end'):
                    ui.button('取消', on_click=dialog.close).props('flat')
                    ui.button('重命名', color='primary',
                              on_click=lambda: rename_current_operation(cur.name, new_name_input.value, dialog)
                              ).props('unelevated')
            dialog.open()

        def rename_current_operation(old_name: str, new_name: str, dialog):
            if not new_name or not new_name.strip():
                logger.warning('新流程名称不能为空')
                return
            if new_name == old_name:
                logger.warning('新名称与原名称相同')
                return
            if new_name in list_available_operations():
                logger.warning(f'流程名称 "{new_name}" 已存在')
                return
            try:
                from operations.config.operation_config import rename_operation
                if rename_operation(old_name, new_name):
                    _save_operation_mgr()
                    refresh_operation_config()
                    logger.info(f'成功重命名工作流程: {old_name} -> {new_name}')
                else:
                    logger.error(f'重命名工作流程失败: {old_name} -> {new_name}')
                dialog.close()
            except Exception as e:
                logger.error(f'重命名工作流程异常: {e}')
                dialog.close()

        ui.button('新建流程', icon='add', on_click=show_create_operation_dialog).props('dense')
        ui.button('重命名当前流程', icon='edit', on_click=show_rename_operation_dialog).props('dense')
        ui.button('删除当前流程', icon='delete', color='negative', on_click=delete_current_operation).props('dense')
        ui.button('复制流程', icon='content_copy', on_click=show_copy_operation_dialog).props('dense')

    # 初次信息显示
    def _initial_refresh_info():
        # 复用 refresh_operation_info 的逻辑
        pass  # 上面 refresh_operation_info 每次 refresh_operation_config 都会调用

    # ---------- 流程配置 ----------
    ui.separator().classes('my-2')
    ui.label('流程配置').classes('text-md font-bold text-blue-600')
    ui.label('条件节点返回 True 时跳到"同 id 的 target"').classes('text-sm text-gray-600 mb-2')

    TYPE_TASK = 'task'
    TYPE_COND = 'condition'
    TYPE_TARGET = 'target'
    TYPE_NOTE = 'note'
    TYPE_SUBFLOW = 'subflow'

    task_choices = list(_TASK_NODE_CLASSES.keys())
    cond_choices = list(_COND_NODE_CLASSES.keys())

    items_container = ui.column().classes('w-full gap-2')

    # ---- 通用控制按钮 ----
    def _render_controls(idx: int):
        with ui.row().classes('items-center justify-end shrink-0 gap-1'):
            ui.button(icon='format_list_numbered',  # 新增：移动到指定序号（固定前插）
                    on_click=lambda e, i=idx: _open_move_dialog(i))\
            .props('dense flat size=sm').classes('text-xs')
            ui.button(icon='arrow_upward',
                    on_click=lambda e, i=idx: (_move_up(i), _render_items()))\
            .props('dense flat size=sm').classes('text-xs')
            ui.button(icon='arrow_downward',
                    on_click=lambda e, i=idx: (_move_down(i), _render_items()))\
            .props('dense flat size=sm').classes('text-xs')
            ui.button(icon='delete', color='negative',
                    on_click=lambda e, i=idx: (_delete(i), _render_items()))\
            .props('dense flat size=sm').classes('text-xs')
            
    # ---- 回写当前 UI 值 ----
    def _save_current_values():
        for item in ctx.nodes_state:
            itype = item.get('type')

            if itype == TYPE_TASK:
                name = item.get('name')
                if name in _TASK_NODE_CLASSES and '__param_widgets' in item:
                    for pname, param in _ctor_params(_TASK_NODE_CLASSES[name]):
                        w = item['__param_widgets'].get(pname)
                        if not w:
                            continue
                        d, a = _param_default_annot(param)
                        v = _read_param_widget(w, a, d)
                        if v is not None:
                            item.setdefault('parameters', {})[pname] = v

            elif itype == TYPE_COND:
                name = item.get('name')
                if name in _COND_NODE_CLASSES and '__param_widgets' in item:
                    for pname, param in _ctor_params(_COND_NODE_CLASSES[name]):
                        w = item['__param_widgets'].get(pname)
                        if not w:
                            continue
                        d, a = _param_default_annot(param)
                        v = _read_param_widget(w, a, d)
                        if v is not None:
                            item.setdefault('parameters', {})[pname] = v
                if '__id_input' in item and hasattr(item['__id_input'], 'value'):
                    item['id'] = item['__id_input'].value
            elif itype == TYPE_NOTE:
                if '__name_input' in item and hasattr(item['__name_input'], 'value'):
                    item['name'] = item['__name_input'].value or ''
                if '__text_input' in item and hasattr(item['__text_input'], 'value'):
                    item.setdefault('parameters', {})['text'] = item['__text_input'].value or ''

    # ---- 下拉更新 ----
    def _on_task_change(new_value: str, i: int):
        if i >= len(ctx.nodes_state):
            return
        _save_current_values()
        if new_value in task_choices:
            ctx.nodes_state[i]['name'] = new_value
            ctx.nodes_state[i]['parameters'] = {}
        _render_items()

    def _on_cond_change(new_value: str, i: int):
        if i >= len(ctx.nodes_state):
            return
        _save_current_values()
        if new_value in cond_choices:
            ctx.nodes_state[i]['name'] = new_value
            ctx.nodes_state[i]['parameters'] = {}
        _render_items()

    def _on_subflow_change(new_value: str, i: int):
        if i >= len(ctx.nodes_state):
            return
        _save_current_values()
        if new_value in list_available_operations():
            ctx.nodes_state[i]['name'] = new_value
            ctx.nodes_state[i]['parameters'] = {}
        _render_items()

    # ---- 三类卡片渲染 ----
    def _render_task_card(idx: int, item: dict):
        kind = 'task'
        with ui.card().classes(_card_classes(kind)):
            with ui.card_section().classes('p-3'):
                with ui.row().classes('items-center w-full gap-3 no-wrap'):
                    ui.icon(STYLE[kind]['icon']).classes(STYLE[kind]['icon_cls'])
                    ui.badge(str(idx + 1)).classes('shrink-0 text-base font-bold')
                    _title_label('Task', kind)

                    # 任务选择
                    sel = ui.select(
                        task_choices,
                        value=item.get('name'),
                        label='任务',
                        clearable=False,
                        on_change=lambda e, i=idx: _on_task_change(e.value, i),
                    ).props('dense outlined').classes('w-56 shrink-0')

                    # 控制按钮
                    _render_controls(idx)

                # 展开项
                with ui.expansion('参数', value=False).classes('w-full mt-2'):
                    with ui.row().classes('items-start gap-3 w-full'):
                        # 参数区
                        param_widgets = {}
                        name = item.get('name')
                        if name in _TASK_NODE_CLASSES:
                            params = _ctor_params(_TASK_NODE_CLASSES[name])
                            if params:
                                with ui.column().classes('gap-2 flex-1'):
                                    for pname, p in params:
                                        cur = (item.get('parameters') or {}).get(pname)
                                        param_widgets[pname] = _create_param_input(pname, p, preset=cur)

                        # 运行按钮
                        btn = ui.button('单步调试', color='primary', icon='play_arrow').classes('text-sm px-3')
                        btn.on('click', lambda: _start_flow_single_task_thread(idx))
                        ctx.step_cards[f'flow_{idx}'] = btn

                # 回写引用
                item['__param_widgets'] = param_widgets
                item['__sel'] = sel

    def _render_cond_card(idx: int, item: dict):
        kind = 'cond'
        with ui.card().classes(_card_classes(kind)):
            with ui.card_section().classes('p-3'):
                with ui.row().classes('items-center w-full gap-3 no-wrap'):
                    ui.icon(STYLE[kind]['icon']).classes(STYLE[kind]['icon_cls'])
                    ui.badge(str(idx + 1)).classes('shrink-0 text-base font-bold')
                    _title_label('Jump if', kind)

                    # 条件类选择
                    sel = ui.select(
                        cond_choices,
                        value=item.get('name'),
                        label='跳转条件',
                        clearable=False,
                        on_change=lambda e, i=idx: _on_cond_change(e.value, i),
                    ).props('dense outlined').classes('w-56 shrink-0')
                    
                    # 控制按钮
                    _render_controls(idx)
                    
                # ID 输入 + 链接提示
                with ui.row().classes('items-center gap-2'):
                    link_icon = ui.icon('link').classes('text-amber-500')
                    ui.tooltip('条件为 True 时跳转到相同 ID 的 Target')
                    id_in = ui.input('节点 ID（与 target 同 id，条件为 True 时跳转）', value=item.get('id', '')
                                    ).props('dense outlined size=sm').classes('w-56')

                # 展开项
                with ui.expansion('参数', value=False).classes('w-full mt-2'):
                    # 参数区
                    param_widgets = {}
                    name = item.get('name')
                    if name in _COND_NODE_CLASSES:
                        params = _ctor_params(_COND_NODE_CLASSES[name])
                        if params:
                            with ui.column().classes('gap-2 flex-1'):
                                for pname, p in params:
                                    cur = (item.get('parameters') or {}).get(pname)
                                    param_widgets[pname] = _create_param_input(pname, p, preset=cur)

                # 回写引用
                item['__id_input'] = id_in
                item['__param_widgets'] = param_widgets
                item['__sel'] = sel

    def _render_target_card(idx: int, item: dict):
        kind = 'target'
        tid = item.get('id', '')
        ref_count = _count_target_refs(tid)
        with ui.card().classes(_card_classes(kind)):
            with ui.card_section().classes('p-3'):
                with ui.row().classes('items-center w-full gap-3 no-wrap'):
                    ui.icon(STYLE[kind]['icon']).classes(STYLE[kind]['icon_cls'])
                    ui.badge(str(idx + 1)).classes('shrink-0 text-base font-bold')
                    _title_label('Target', kind)

                    # 只读 ID
                    id_in = ui.input('目标 ID（应等于对应条件的 ID，条件为 True 时跳转到此）', value=tid
                                    ).props('dense outlined size=sm readonly').classes('w-56')

                    # # 被引用统计（小徽章）
                    # with ui.row().classes('items-center gap-1'):
                    #     ui.icon('call_merge').classes('text-emerald-500')
                    #     ui.label(f'被 {ref_count} 个条件引用').classes('text-sm text-emerald-700')
                    #     ui.tooltip('统计与该 ID 相同的 Condition 数量（便于快速校验）')

                    # 控制按钮
                    _render_controls(idx)

                    # 回写引用
                    item['__id_input_target'] = id_in
                    
    def _render_note_card(idx: int, item: dict):
        kind = 'note'
        note_id = item.get('id', '')
        title = item.get('name', '')
        text_val = (item.get('parameters') or {}).get('text', '')

        with ui.card().classes(_card_classes(kind)):
            with ui.card_section().classes('p-3'):
                with ui.row().classes('items-center w-full gap-3 no-wrap'):
                    ui.icon(STYLE[kind]['icon']).classes(STYLE[kind]['icon_cls'])
                    ui.badge(str(idx + 1)).classes('shrink-0 text-base font-bold')
                    _title_label('Note', kind)

                    # 注释内容
                    text_in = ui.textarea('注释内容', value=text_val)\
                                .props('dense outlined autogrow').classes('w-56 min-h-[40px]')

                    # 控制按钮
                    _render_controls(idx)

                # 回写引用，供保存/状态回写使用
                item['__text_input'] = text_in

    def _render_subflow_card(idx: int, item: dict):
        kind = 'subflow'
        with ui.card().classes(_card_classes(kind)):
            with ui.card_section().classes('p-3'):
                with ui.row().classes('items-center w-full gap-3 no-wrap'):
                    ui.icon(STYLE[kind]['icon']).classes(STYLE[kind]['icon_cls'])
                    ui.badge(str(idx + 1)).classes('shrink-0 text-base font-bold')
                    _title_label('Subflow', kind)

                    # 流程选择
                    flow_choices = list_available_operations()
                    sel = ui.select(
                        flow_choices,
                        value=item.get('name'),
                        label='子流程',
                        clearable=False,
                        on_change=lambda e, i=idx: _on_subflow_change(e.value, i),
                    ).props('dense outlined').classes('w-56 shrink-0')

                    # 控制按钮
                    _render_controls(idx)

                # 回写引用
                item['__sel'] = sel



    # ---- 列表渲染入口 ----
    def _render_items():
        items_container.clear()
        for idx, item in enumerate(ctx.nodes_state):
            with items_container:
                t = item.get('type', TYPE_TASK)
                if t == TYPE_TASK:
                    _render_task_card(idx, item)
                elif t == TYPE_COND:
                    _render_cond_card(idx, item)
                elif t == TYPE_TARGET:
                    _render_target_card(idx, item)
                elif t == TYPE_NOTE:
                    _render_note_card(idx, item)
                elif t == TYPE_SUBFLOW:
                    _render_subflow_card(idx, item)
                else:
                    with ui.card().classes('w-full mb-2'):
                        with ui.card_section().classes('p-3'):
                            ui.label(f'未知节点类型: {t}').classes('text-red-600')

    # ---- 结构操作 ----
    def _move_up(i: int):
        _save_current_values()
        if i > 0:
            ctx.nodes_state[i - 1], ctx.nodes_state[i] = ctx.nodes_state[i], ctx.nodes_state[i - 1]

    def _move_down(i: int):
        _save_current_values()
        if i < len(ctx.nodes_state) - 1:
            ctx.nodes_state[i + 1], ctx.nodes_state[i] = ctx.nodes_state[i], ctx.nodes_state[i + 1]

    def _delete(i: int):
        _save_current_values()
        ctx.nodes_state.pop(i)
        
    def _move_to_position(src_i: int, dest_1based: int):
        """把索引 src_i 的节点移动到“目标序号”之前（序号从 1 开始，固定前插）"""
        _save_current_values()
        n = len(ctx.nodes_state)
        if n <= 1 or src_i < 0 or src_i >= n:
            return

        try:
            dest_1 = int(dest_1based or 1)
        except Exception:
            dest_1 = 1
        dest_1 = max(1, min(n, dest_1))   # 归一化到 1..n
        dest0 = dest_1 - 1                # 转 0 基

        item = ctx.nodes_state.pop(src_i)
        if src_i < dest0:                 # 从上往下移时，弹出后目标位左移一格
            dest0 -= 1
        dest0 = max(0, min(len(ctx.nodes_state), dest0))
        ctx.nodes_state.insert(dest0, item)
        _render_items()


    def _open_move_dialog(i: int):
        """弹窗：输入目标序号，按固定规则插入到该序号之前"""
        n = len(ctx.nodes_state)
        with ui.dialog() as d, ui.card():
            with ui.card_section():
                ui.label(f'移动节点 #{i + 1}').classes('text-lg font-bold')
            with ui.card_section():
                target_no = ui.number(f'目标序号（1 - {n}）',
                                    value=min(n, i + 1),
                                    format='%.0f').props('dense outlined').classes('w-36')
                ui.label('规则：插入到目标序号之前').classes('text-xs text-gray-500 mt-1')
            with ui.card_actions().classes('justify-end'):
                ui.button('取消', on_click=d.close).props('flat')
                def _confirm():
                    _move_to_position(i, target_no.value or 1)
                    d.close()
                ui.button('确定', color='primary', on_click=_confirm).props('unelevated')
        d.open()

    # ---- 新增节点 ----
    def _add_task_item():
        _save_current_values()
        ctx.nodes_state.append({
            'type': TYPE_TASK,
            'name': (next(iter(_TASK_NODE_CLASSES.keys()), '') if _TASK_NODE_CLASSES else ''),
            'parameters': {},
        })
        _render_items()

    def _add_condition_item():
        _save_current_values()
        next_idx = len([x for x in ctx.nodes_state if x.get('type') == TYPE_COND]) + 1
        cid = f'cond_{next_idx}'
        ctx.nodes_state.append({
            'type': TYPE_COND,
            'id': cid,
            'name': (next(iter(_COND_NODE_CLASSES.keys()), '') if _COND_NODE_CLASSES else ''),
            'parameters': {},
        })
        ctx.nodes_state.append({'type': TYPE_TARGET, 'id': cid, 'name': 'TargetAnchor'})
        _render_items()

    def _add_note_item():
        _save_current_values()
        ctx.nodes_state.append({
            'type': TYPE_NOTE,
            'id': '',           # 可留空，保存时自动生成
            'name': '注释',      # 默认标题
            'parameters': {'text': ''},
        })
        _render_items()

    def _add_subflow_item():
        _save_current_values()
        available_ops = list_available_operations()
        default_flow = available_ops[0] if available_ops else ''
        ctx.nodes_state.append({
            'type': TYPE_SUBFLOW,
            'id': '',
            'name': default_flow,
            'parameters': {},
        })
        _render_items()

    # ---- 保存配置 ----
    def _save_items():
        """UI -> cfg.nodes：保留显式 target 的原始顺序；缺失的 target 才在末尾自动补"""
        _save_current_values()

        # 预扫：收集所有 condition 的 id（保持顺序以便统计缺失）
        all_cond_ids: list[str] = [
            it.get('id') for it in ctx.nodes_state
            if it.get('type') == TYPE_COND and it.get('id')
        ] # type: ignore
        cond_id_set = set(all_cond_ids)

        new_nodes: List[OperationNodeConfig] = []
        explicit_target_ids: set[str] = set()

        # 统计信息（用于日志）
        original_target_count = sum(1 for it in ctx.nodes_state if it.get('type') == TYPE_TARGET)
        invalid_target_count = sum(
            1 for it in ctx.nodes_state
            if it.get('type') == TYPE_TARGET and (it.get('id', '') not in cond_id_set)
        )

        for idx, item in enumerate(ctx.nodes_state, start=1):
            t = item.get('type', TYPE_TASK)

            if t == TYPE_TASK:
                name = getattr(item.get('__sel'), 'value', item.get('name')) if item.get('__sel') else item.get('name')
                params = {}
                if name in _TASK_NODE_CLASSES:
                    for pname, p in _ctor_params(_TASK_NODE_CLASSES[name]):
                        w = (item.get('__param_widgets') or {}).get(pname)
                        if not w:
                            continue
                        d, a = _param_default_annot(p)
                        v = _read_param_widget(w, a, d)
                        if v is not None:
                            params[pname] = v
                new_nodes.append(OperationNodeConfig(type=TYPE_TASK, id=f'task_{idx}', name=name, parameters=params)) # type: ignore

            elif t == TYPE_COND:
                node_id = getattr(item.get('__id_input'), 'value', item.get('id')) if item.get('__id_input') else (item.get('id') or f'cond_{idx}')
                name = getattr(item.get('__sel'), 'value', item.get('name')) if item.get('__sel') else item.get('name')
                params = {}
                if name in _COND_NODE_CLASSES:
                    for pname, p in _ctor_params(_COND_NODE_CLASSES[name]):
                        w = (item.get('__param_widgets') or {}).get(pname)
                        if not w:
                            continue
                        d, a = _param_default_annot(p)
                        v = _read_param_widget(w, a, d)
                        if v is not None:
                            params[pname] = v
                new_nodes.append(OperationNodeConfig(type=TYPE_COND, id=node_id, name=name, parameters=params)) # type: ignore

            elif t == TYPE_SUBFLOW:
                name = getattr(item.get('__sel'), 'value', item.get('name')) if item.get('__sel') else item.get('name')
                params = {'subflow_name': name}
                new_nodes.append(OperationNodeConfig(type=TYPE_SUBFLOW, id=f'subflow_{idx}', name='', parameters=params)) # type: ignore

            elif t == TYPE_TARGET:
                # 注意：无论 target 在 condition 上/下方，都以“预扫集合”判断合法性，并按当前位置保存
                t_id = getattr(item.get('__id_input_target'), 'value', item.get('id', '')) if item.get('__id_input_target') else item.get('id', '')
                t_name = item.get('name', 'TargetAnchor')
                if t_id in cond_id_set:
                    new_nodes.append(OperationNodeConfig(type=TYPE_TARGET, id=t_id, name=t_name, parameters={}))
                    explicit_target_ids.add(t_id)
                # else: 跳过无效 target（未找到同 id 的 condition）
            elif t == TYPE_NOTE:
                # 生成/读取 note 的 id（可留空，也可自动生成）
                node_id = item.get('id') or f'note_{idx}'
                # 标题（name）
                name = getattr(item.get('__name_input'), 'value', item.get('name')) if item.get('__name_input') else item.get('name', '')
                # 正文（parameters['text']）
                text_val = getattr(item.get('__text_input'), 'value', (item.get('parameters') or {}).get('text', '')) \
                        if item.get('__text_input') else (item.get('parameters') or {}).get('text', '')
                params = {'text': text_val}
                new_nodes.append(OperationNodeConfig(type=TYPE_NOTE, id=node_id, name=name, parameters=params)) # type: ignore


        # 为缺少显式 target 的 condition 自动补一个（在末尾）
        missing_ids = [cid for cid in all_cond_ids if cid not in explicit_target_ids]
        for cid in missing_ids:
            new_nodes.append(OperationNodeConfig(type=TYPE_TARGET, id=cid, name='TargetAnchor', parameters={}))

        try:
            cur = get_current_operation()
            cur.nodes = new_nodes
            save_current_operation(cur)
            save_operation_manager()

            msgs = []
            if invalid_target_count > 0:
                msgs.append(f'清理了 {invalid_target_count} 个无效 target')
            if missing_ids:
                msgs.append(f'为 {len(missing_ids)} 个条件自动补充 target')
            logger.info('配置已保存' + (f'；{"; ".join(msgs)}' if msgs else ''))
        except Exception as e:
            logger.error(f'保存失败: {e}')

    # 顶部动作按钮
    with ui.row().classes('gap-2 mt-1'):
        ui.button('新增任务节点', icon='add', on_click=_add_task_item).props('dense')
        ui.button('新增条件节点', icon='add_alert', on_click=_add_condition_item).props('dense')
        ui.button('新增注释节点', icon='sticky_note_2', on_click=_add_note_item).props('dense')
        ui.button('新增子流程节点', icon='call_split', on_click=_add_subflow_item).props('dense')
        ui.button('保存配置', color='primary', icon='save', on_click=_save_items).props('dense')

    # 初次渲染
    if not ctx.nodes_state:
        ctx.nodes_state.append({'type': TYPE_TASK, 'name': next(iter(_TASK_NODE_CLASSES.keys()), ''), 'parameters': {}})
    _render_items()

    # ---------- 运行/停止 ----------
    _previous_running_state = [False]

    def _update_button_states():
        running = is_task_process_running()
        if _previous_running_state[0] and not running:
            current_cfg = get_current_operation()
            logger.info(f'流程 "{current_cfg.name}" 已结束')
        _previous_running_state[0] = running

        # 单步卡片按钮
        for btn in ctx.step_cards.values():
            btn.props('loading' if running else 'loading=false')

        # 运行/停止按钮
        if ctx.run_full_btn:
            ctx.run_full_btn.props('loading' if running else 'loading=false')
        if ctx.stop_btn:
            ctx.stop_btn.props('disable=false' if running else 'disable=true')

    def _on_run_config_sequence_click():
        if is_task_process_running():
            logger.warning('已有任务在运行中')
            return
        current_cfg = get_current_operation()
        nodes_count = len(getattr(current_cfg, 'nodes', []) or [])
        if nodes_count == 0:
            logger.warning('没有配置任何节点，请先添加并保存')
            return
        try:
            logger.info(f'开始运行流程 "{current_cfg.name}"，共 {nodes_count} 个节点')
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
        ctx.run_full_btn = ui.button('运行配置顺序', color='secondary', icon='play_arrow')
        ctx.run_full_btn.on('click', _on_run_config_sequence_click)
        ctx.stop_btn = ui.button('停止', color='negative', icon='stop').props('disable=true')
        ctx.stop_btn.on('click', _on_stop_click)

    ui.timer(1.0, _update_button_states)




