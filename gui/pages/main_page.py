from nicegui import ui
from core.logger import logger
from tasks.run_tasks import start_step_thread
from tasks.debug_vars import get_debug_vars, get_debug_images
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

def render_main_page():
    ui.markdown("# RoboGame2025 控制界面")

    from tasks.run_tasks import _STEP_CLASSES
    step_options = list(_STEP_CLASSES.keys())

    selected_step = ui.select(step_options, label="选择要调试的步骤")

    run_btn = ui.button("运行选中步骤")
    status_card = ui.card()
    with status_card:
        ui.label('调试变量区域：等待运行...')

    # 固定图片槽位（最多两个）
    with ui.row():
        with ui.column():
            img_slot_1_label = ui.label('图片1（空）')
            img_slot_1 = ui.interactive_image(get_empty_img())
            
        with ui.column():
            img_slot_2_label = ui.label('图片2（空）')
            img_slot_2 = ui.interactive_image(get_empty_img())
            

    def refresh_debug():
        data = get_debug_vars()
        images = list(get_debug_images())
        if not data:
            return
        lines = []
        images = []
        for k, v in data.items():
            lines.append(f"{str(k)}: {str(v)}")
        with status_card:
            status_card.clear()
            if len(lines) <=0:
                ui.label('(无文本调试变量)')
            else:
                for line in lines:
                    ui.label(line)
        # 处理固定槽位前两个
        if images:
            # 第一个槽位
            name1, meta1 = images[0]
            src1 = prepare_image_for_display(meta1.get(data))
            img_slot_1.set_source(src1)
            img_slot_1_label.set_text(name1)
        else:
            img_slot_1.set_source(get_empty_img())
            img_slot_1_label.set_text('图片1 (空)')
        if len(images) > 1:
            name2, meta2 = images[1]
            src2 = prepare_image_for_display(meta2.get(data))
            img_slot_2.set_source(src2)
            img_slot_2_label.set_text(name2)
        else:
            img_slot_2.set_source(get_empty_img())
            img_slot_2_label.set_text('图片2 (空)')

    ui.timer(0.5, refresh_debug)

    def _on_run_click():
        step_name = selected_step.value
        if not step_name:
            ui.notify("请选择一个步骤", type="warning")
            return
        logger.info(f"开始运行步骤: {step_name}")
        start_step_thread(step_name)
        ui.notify(f"{step_name} 已启动", type="info")

    run_btn.on('click', _on_run_click)
    
