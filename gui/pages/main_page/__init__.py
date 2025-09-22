from nicegui import ui
from .tasks_panel import render_tasks_panel
from .debug_panel import render_debug_panel


def render_main_page():
    ui.markdown('# RoboGame2025')
    render_tasks_panel()
    ui.separator()
    render_debug_panel()