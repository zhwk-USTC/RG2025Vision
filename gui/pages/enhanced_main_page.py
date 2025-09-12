from nicegui import ui
from core.logger import logger
from tasks.run_tasks import start_step_thread, force_stop_current_task, is_task_running
from tasks.debug_vars_enhanced import (
    get_enhanced_vars, get_enhanced_images, get_debug_summary,
    DebugLevel, DebugCategory
)
from PIL import Image
import numpy as np
from typing import Optional, Union

def np_to_pil(img_np):
    if img_np is None:
        return get_empty_img()
    if isinstance(img_np, Image.Image):
        return img_np
    return Image.fromarray(img_np.astype('uint8'), 'RGB')

def get_empty_img():
    return Image.new("RGB", (320, 240), (200, 200, 200))

def prepare_image_for_display(img_np: Optional[Union[np.ndarray, Image.Image]]) -> Image.Image:
    """将numpy数组或PIL图像转换为适合显示的PIL格式"""
    if img_np is None:
        return get_empty_img()
    
    # 转换为PIL图像
    pil_img = np_to_pil(img_np)

    # 缩放到最大宽度 320px
    max_width = 320
    if pil_img.width > max_width:
        ratio = max_width / pil_img.width
        new_size = (max_width, int(pil_img.height * ratio))
        pil_img = pil_img.resize(new_size)

    # 转换为RGB格式（如果需要）
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')

    return pil_img

def get_level_color(level: DebugLevel) -> str:
    """根据调试级别获取颜色"""
    colors = {
        DebugLevel.INFO: "blue",
        DebugLevel.WARNING: "orange", 
        DebugLevel.ERROR: "red",
        DebugLevel.SUCCESS: "green"
    }
    return colors.get(level, "gray")

def get_category_icon(category: DebugCategory) -> str:
    """根据分类获取图标"""
    icons = {
        DebugCategory.STATUS: "info",
        DebugCategory.POSITION: "location_on",
        DebugCategory.DETECTION: "visibility",
        DebugCategory.CONTROL: "gamepad",
        DebugCategory.TIMING: "schedule",
        DebugCategory.ERROR: "error",
        DebugCategory.IMAGE: "image"
    }
    return icons.get(category, "help")

def render_enhanced_main_page():
    ui.markdown("# RoboGame2025 增强调试界面")

    from tasks.run_tasks import _STEP_CLASSES
    step_options = list(_STEP_CLASSES.keys())

    with ui.row().classes('w-full'):
        # 左侧控制面板
        ui.markdown("## 控制面板")
        
        # 运行步骤和汇总在一行
        with ui.row().classes('w-full gap-2'):
            # 运行步骤
            with ui.column().classes('w-1/2'):
                selected_step = ui.select(step_options, label="选择要调试的步骤")
                with ui.row().classes('gap-2'):
                    run_btn = ui.button("运行选中步骤", color="primary")
                    stop_btn = ui.button("强制停止", color="negative").props('icon=stop disable')
            
            # 汇总信息
            with ui.column().classes('w-1/2'):
                summary_card = ui.card().classes('w-full')
                with summary_card:
                    ui.label('调试汇总').classes('text-lg font-bold')
                    summary_content = ui.column()

        # 右侧主要内容区域
        # 图像显示区域（放在上方）
        ui.markdown("## 图像显示")
        with ui.card().classes('w-full mb-6'):
            with ui.card_section():
                images_content = ui.row().classes('flex-wrap')
        
        # 调试变量区域
        ui.markdown("## 调试变量")
        
        # 使用网格布局显示所有变量类别
        with ui.grid(columns=2).classes('w-full gap-4'):
            # 左列卡片
            # 状态变量卡片
            with ui.card().classes('w-full'):
                with ui.card_section():
                    with ui.row().classes('items-center'):
                        ui.icon('info', color='blue')
                        ui.label('状态变量').classes('text-lg font-bold')
                    status_content = ui.column().classes('mt-2')
            
            # 检测变量卡片
            with ui.card().classes('w-full'):
                with ui.card_section():
                    with ui.row().classes('items-center'):
                        ui.icon('visibility', color='purple')
                        ui.label('检测变量').classes('text-lg font-bold')
                    detection_content = ui.column().classes('mt-2')
            
            # 位置变量卡片  
            with ui.card().classes('w-full'):
                with ui.card_section():
                    with ui.row().classes('items-center'):
                        ui.icon('location_on', color='green')
                        ui.label('位置变量').classes('text-lg font-bold')
                    position_content = ui.column().classes('mt-2')
            
            # 时间变量卡片
            with ui.card().classes('w-full'):
                with ui.card_section():
                    with ui.row().classes('items-center'):
                        ui.icon('schedule', color='orange')
                        ui.label('时间变量').classes('text-lg font-bold')
                    timing_content = ui.column().classes('mt-2')
            
            # 控制变量卡片
            with ui.card().classes('w-full'):
                with ui.card_section():
                    with ui.row().classes('items-center'):
                        ui.icon('gamepad', color='teal')
                        ui.label('控制变量').classes('text-lg font-bold')
                    control_content = ui.column().classes('mt-2')
            
            # 错误变量卡片
            with ui.card().classes('w-full'):
                with ui.card_section():
                    with ui.row().classes('items-center'):
                        ui.icon('error', color='red')
                        ui.label('错误变量').classes('text-lg font-bold')
                    error_content = ui.column().classes('mt-2')

    def refresh_debug():
        # 获取增强版调试数据
        vars_data = get_enhanced_vars()
        images_data = get_enhanced_images()
        summary = get_debug_summary()
        
        # 更新按钮状态
        _update_button_states()
        
        # 更新汇总信息
        with summary_content:
            summary_content.clear()
            ui.label(f"变量总数: {summary.get('total_vars', 0)}")
            ui.label(f"图像总数: {summary.get('total_images', 0)}")
            
            # 按级别显示计数
            level_counts = summary.get('by_level', {})
            if level_counts:
                with ui.row():
                    for level, count in level_counts.items():
                        color = get_level_color(DebugLevel(level))
                        ui.badge(f"{level}: {count}", color=color)
        
        # 按分类更新内容 - 所有类别同时显示
        categories_content = {
            DebugCategory.STATUS: status_content,
            DebugCategory.POSITION: position_content, 
            DebugCategory.DETECTION: detection_content,
            DebugCategory.CONTROL: control_content,
            DebugCategory.TIMING: timing_content,
            DebugCategory.ERROR: error_content
        }
        
        for category, content_area in categories_content.items():
            with content_area:
                content_area.clear()
                category_vars = {k: v for k, v in vars_data.items() if v.category == category}
                
                if not category_vars:
                    ui.label(f'暂无数据').classes('text-gray-500 text-sm')
                else:
                    for key, entry in category_vars.items():
                        color = get_level_color(entry.level)
                        
                        # 使用更紧凑的显示格式
                        with ui.row().classes('items-center mb-1 p-2 bg-gray-50 rounded'):
                            ui.badge(entry.level.value, color=color).classes('mr-2')
                            with ui.column().classes('flex-grow'):
                                ui.label(f"{key}: {entry.value}").classes('font-medium text-sm')
                                if entry.description:
                                    ui.label(entry.description).classes('text-xs text-gray-600')
                                ui.label(entry.timestamp.strftime('%H:%M:%S')).classes('text-xs text-gray-400')
        
        # 更新图像显示 - 水平排列在顶部
        with images_content:
            images_content.clear()
            if not images_data:
                ui.label('暂无图像数据').classes('text-gray-500 text-center w-full')
            else:
                for key, entry in list(images_data.items())[:4]:  # 最多显示4个图像
                    with ui.column().classes('mr-4'):
                        ui.label(key).classes('font-bold text-sm text-center')
                        if entry.description:
                            ui.label(entry.description).classes('text-xs text-gray-600 text-center mb-2')
                        
                        try:
                            prepared_img = prepare_image_for_display(entry.image)
                            ui.interactive_image(prepared_img).classes('max-w-xs')
                        except Exception as e:
                            ui.label(f'图像显示错误: {e}').classes('text-red-500 text-xs')
                        
                        with ui.column().classes('items-center mt-1'):
                            ui.label(entry.timestamp.strftime('%H:%M:%S')).classes('text-xs text-gray-400')
                            if entry.size:
                                ui.label(f"{entry.size}").classes('text-xs text-gray-400')

    # 定时刷新
    ui.timer(0.5, refresh_debug)

    def _on_run_click():
        step_name = selected_step.value
        if not step_name:
            ui.notify("请选择一个步骤", type="warning")
            return
        
        if is_task_running():
            ui.notify("已有任务在运行中，请先停止当前任务", type="warning")
            return
            
        logger.info(f"开始运行步骤: {step_name}")
        start_step_thread(step_name)
        ui.notify(f"{step_name} 已启动", type="positive")
        
        # 更新按钮状态
        run_btn.props('loading')
        stop_btn.props('disable=false')

    def _on_stop_click():
        if not is_task_running():
            ui.notify("当前没有正在运行的任务", type="info")
            return
            
        logger.info("用户请求强制停止当前任务")
        force_stop_current_task()
        ui.notify("任务已被强制停止", type="warning")
        
        # 更新按钮状态
        run_btn.props('loading=false')
        stop_btn.props('disable=true')

    def _update_button_states():
        """更新按钮状态"""
        if is_task_running():
            run_btn.props('loading')
            stop_btn.props('disable=false')
        else:
            run_btn.props('loading=false')
            stop_btn.props('disable=true')

    run_btn.on('click', _on_run_click)
    stop_btn.on('click', _on_stop_click)
    
    # 定时更新按钮状态
    ui.timer(1.0, _update_button_states)