from nicegui import ui
from .tasks_panel import get_current_operation, render_single_step_panel, render_flow_panel, UIPanelContext, _cfg_nodes_to_state
from .debug_panel import render_debug_panel
from gui.utils.tab_memory import create_memorable_tabs

def render_main_page():
    ui.markdown('# RoboGame2025')
    ui.markdown('## 控制面板')

    cfg = get_current_operation()
    nodes_state = _cfg_nodes_to_state(cfg)
    ctx = UIPanelContext(nodes_state=nodes_state)
    
    def _render_single():
        render_single_step_panel(ctx)

    def _render_flow():
        render_flow_panel(ctx)

    tab_configs = {
        'single': ('单步调试', _render_single),
        'flow':  ('流程', _render_flow),
        'debug': ('调试参数', render_debug_panel),
    }

    create_memorable_tabs(memory_key='tasks_panel_tabs', tab_configs=tab_configs, default_tab='flow')
