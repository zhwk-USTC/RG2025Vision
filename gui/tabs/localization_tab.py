"""
定位配置界面
用于配置摄像头位置、场地标签位置等定位参数
"""

from nicegui import ui
import numpy as np
from vision.localization import Localization, CameraPose, TagPose
from core.logger import logger


def render_localization_tab():
    """渲染定位配置界面"""
    
    ui.markdown('# 定位配置')

    # 1. 场地布局可视化（用空白SVG填充）
    with ui.card().classes('q-pa-md q-mb-md').style('width: 100%'):
        ui.markdown('## 场地布局可视化')
        blank_svg = '<svg width="400" height="300" style="border: 1px solid #ccc; background: #f9f9f9;"></svg>'
        ui.html(blank_svg)
        ui.label('此处为场地布局预览（空白）').classes('text-caption')

    # 2. 摄像头位置配置
    with ui.card().classes('q-pa-md q-mb-md').style('width: 100%'):
        ui.markdown('## 摄像头位置配置')
        ui.markdown('配置每个摄像头相对于小车中心的位置和角度')
        camera_configs = []
        with ui.row().classes('q-gutter-md'):
            for i in range(3):
                with ui.column().classes('q-gutter-sm').style('flex: 1'):
                    ui.label(f'摄像头 {i}').classes('text-h6 text-center')
                    if i < len(robot_localizer.camera_poses):
                        pose = robot_localizer.camera_poses[i]
                        x_val, y_val, yaw_val = pose.x, pose.y, pose.yaw
                    else:
                        x_val, y_val, yaw_val = 0.0, 0.0, 0.0
                    x_input = ui.number('X坐标 (m)', value=x_val, step=0.01, format='%.3f').classes('w-full')
                    y_input = ui.number('Y坐标 (m)', value=y_val, step=0.01, format='%.3f').classes('w-full')
                    yaw_input = ui.number('角度 (度)', value=np.degrees(yaw_val), step=1, format='%.1f').classes('w-full')
                    camera_configs.append({
                        'x': x_input,
                        'y': y_input,
                        'yaw': yaw_input
                    })
        def save_camera_config():
            robot_localizer.camera_poses = []
            for i, config in enumerate(camera_configs):
                try:
                    x = config['x'].value
                    y = config['y'].value
                    yaw = np.radians(config['yaw'].value)
                    robot_localizer.camera_poses.append(CameraPose(x, y, yaw))
                    logger.info(f"摄像头 {i} 配置: ({x:.3f}, {y:.3f}), 角度: {np.degrees(yaw):.1f}°")
                except Exception as e:
                    logger.error(f"摄像头 {i} 配置错误: {e}")
            robot_localizer.save_config()
            ui.notify('摄像头配置已保存', type='positive')
        ui.button('保存摄像头配置', on_click=save_camera_config, color='primary').classes('w-full q-mt-md')

    # 3. 场地AprilTag配置（仅 x, y, yaw）
    with ui.card().classes('q-pa-md q-mb-md').style('width: 100%'):
        ui.markdown('## 场地AprilTag配置')
        ui.markdown('场地中每个AprilTag的位置（readonly）')
        with ui.column().classes('q-gutter-sm'):
            tag_table_data = []
            for tag_id, tag in robot_localizer.field_tags.items():
                tag_table_data.append({
                    'id': tag_id,
                    'x': f'{tag.x:.3f}',
                    'y': f'{tag.y:.3f}',
                    'yaw': f'{np.degrees(tag.yaw):.1f}°'
                })
            ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id'},
                    {'name': 'x', 'label': 'X (m)', 'field': 'x'},
                    {'name': 'y', 'label': 'Y (m)', 'field': 'y'},
                    {'name': 'yaw', 'label': '角度', 'field': 'yaw'},
                ],
                rows=tag_table_data
            ).classes('w-full')
