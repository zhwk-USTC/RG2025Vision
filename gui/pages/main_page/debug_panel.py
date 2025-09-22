from nicegui import ui
from core.logger import logger
from gui.utils import get_empty_img, prepare_image_for_display

from operations.debug_vars_enhanced import (
    get_enhanced_vars,
    get_enhanced_images,
    get_debug_summary,
    DebugLevel,
    DebugCategory,
)


def get_level_color(level: DebugLevel) -> str:
    return {
        DebugLevel.INFO: "blue",
        DebugLevel.WARNING: "orange",
        DebugLevel.ERROR: "red",
        DebugLevel.SUCCESS: "green",
    }.get(level, "gray")

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
