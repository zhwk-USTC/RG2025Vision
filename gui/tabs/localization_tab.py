"""
定位配置界面
用于配置摄像头位置、场地标签位置等定位参数
"""

from nicegui import ui
import numpy as np
from vision.localization import robot_localizer, CameraPose, AprilTagPose
from core.logger import logger


def render_localization_tab():
    """渲染定位配置界面"""
    
    ui.markdown('# 定位配置')

    # 1. 场地布局可视化
    with ui.card().classes('q-pa-md q-mb-md').style('width: 100%'):
        ui.markdown('## 场地布局可视化')
        # 1. 加载场地SVG（假设assets/field.svg为场地文件）
        import os
        scale_factor = 0.002  # 场地渲染缩放倍数（例如0.2表示缩小为原来的20%）
        field_svg_path = os.path.join(os.path.dirname(__file__), '../../assets/field.svg')
        field_svg_content = ''
        try:
            with open(field_svg_path, 'r', encoding='utf-8') as f:
                field_svg_content = f.read()
        except Exception:
            # 如果没有场地文件则用空白SVG
            field_svg_content = '<svg width="500" height="800" viewBox="-1 -1 5 4" style="border: 1px solid #ccc; background: #f9f9f9;"></svg>'

        # 2. 获取机器人当前位置和朝向（如果有）
        robot_x, robot_y, robot_theta = 2.0, 1.5, 0.0  # 默认场地中心，朝向右
        try:
            if hasattr(robot_localizer, 'last_position') and robot_localizer.last_position:
                robot_x, robot_y, robot_theta = robot_localizer.last_position
        except Exception:
            pass
        # 加载静态car.svg group内容
        car_svg_path = os.path.join(os.path.dirname(__file__), '../../assets/car.svg')
        car_group = ''
        try:
            with open(car_svg_path, 'r', encoding='utf-8') as f:
                car_group = f.read()
        except Exception:
            car_group = ''
        # 主SVG中定义marker，叠加小车group并整体transform（加缩放）
        robot_svg = f'''
        <svg width="400" height="300" viewBox="-1 -1 5 4" style="position:absolute;top:0;left:0;pointer-events:none;">
            <defs>
                <marker id="arrowhead" markerWidth="4" markerHeight="4" refX="2" refY="2" orient="auto" markerUnits="strokeWidth">
                    <path d="M0,0 L4,2 L0,4 L1,2 Z" fill="#1976d2" />
                </marker>
            </defs>
            <g transform="scale({scale_factor}) translate({robot_x},{robot_y}) rotate({np.degrees(robot_theta)})">
                {car_group}
            </g>
        </svg>
        '''
        # 3. 叠加显示（场地SVG整体缩放）
        ui.html(f'<div style="position:relative;width:400px;height:300px;">'
                f'<div style="transform:scale({scale_factor});transform-origin:0 0;">{field_svg_content}</div>'
                f'{robot_svg}'
                f'</div>')
        ui.label(f'红色箭头: 小车当前位置和朝向，场地缩放倍数：{scale_factor}').classes('text-caption')

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
                        x_val, y_val, angle_val = pose.x, pose.y, pose.angle
                        fov_val = pose.fov
                    else:
                        x_val, y_val, angle_val, fov_val = 0.0, 0.0, 0.0, np.pi/3
                    x_input = ui.number('X坐标 (m)', value=x_val, step=0.01, format='%.3f').classes('w-full')
                    y_input = ui.number('Y坐标 (m)', value=y_val, step=0.01, format='%.3f').classes('w-full')
                    angle_input = ui.number('角度 (度)', value=np.degrees(angle_val), step=1, format='%.1f').classes('w-full')
                    fov_input = ui.number('视场角 (度)', value=np.degrees(fov_val), step=5, format='%.1f').classes('w-full')
                    camera_configs.append({
                        'x': x_input,
                        'y': y_input,
                        'angle': angle_input,
                        'fov': fov_input
                    })
        def save_camera_config():
            robot_localizer.camera_poses = []
            for i, config in enumerate(camera_configs):
                try:
                    x = config['x'].value
                    y = config['y'].value
                    angle = np.radians(config['angle'].value)
                    fov = np.radians(config['fov'].value)
                    robot_localizer.camera_poses.append(CameraPose(x, y, angle, fov))
                    logger.info(f"摄像头 {i} 配置: ({x:.3f}, {y:.3f}), 角度: {np.degrees(angle):.1f}°")
                except Exception as e:
                    logger.error(f"摄像头 {i} 配置错误: {e}")
            robot_localizer.save_config()
            ui.notify('摄像头配置已保存', type='positive')
        ui.button('保存摄像头配置', on_click=save_camera_config, color='primary').classes('w-full q-mt-md')

    # 3. 场地AprilTag配置
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
                    'angle': f'{np.degrees(tag.angle):.1f}°'
                })
            ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id'},
                    {'name': 'x', 'label': 'X (m)', 'field': 'x'},
                    {'name': 'y', 'label': 'Y (m)', 'field': 'y'},
                    {'name': 'angle', 'label': '角度', 'field': 'angle'},
                ],
                rows=tag_table_data
            ).classes('w-full')
