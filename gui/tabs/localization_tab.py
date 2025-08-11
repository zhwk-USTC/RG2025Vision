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
    
    # 摄像头配置区域
    with ui.card().classes('q-pa-md q-mb-md').style('width: 100%'):
        ui.markdown('## 摄像头位置配置')
        ui.markdown('配置每个摄像头相对于小车中心的位置和角度')
        
        camera_configs = []
        
        # 三个摄像头配置在一行中
        with ui.row().classes('q-gutter-md'):
            for i in range(3):  # 三个摄像头
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
    
    # 场地标签配置
    with ui.card().classes('q-pa-md q-mb-md').style('width: 100%'):
        ui.markdown('## 场地AprilTag配置')
        ui.markdown('配置场地中每个AprilTag的位置')
        
        # 显示现有标签
        with ui.column().classes('q-gutter-sm'):
            ui.label('现有标签:').classes('text-h6')
            
            tag_table_data = []
            for tag_id, tag in robot_localizer.field_tags.items():
                tag_table_data.append({
                    'id': tag_id,
                    'x': f'{tag.x:.3f}',
                    'y': f'{tag.y:.3f}',
                    'angle': f'{np.degrees(tag.angle):.1f}°'
                })
            
            tag_table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id'},
                    {'name': 'x', 'label': 'X (m)', 'field': 'x'},
                    {'name': 'y', 'label': 'Y (m)', 'field': 'y'},
                    {'name': 'angle', 'label': '角度', 'field': 'angle'},
                ],
                rows=tag_table_data
            ).classes('w-full')
            
            # 添加新标签
            ui.separator()
            ui.label('添加新标签:').classes('text-h6')
            
            with ui.row().classes('q-gutter-sm'):
                new_id_input = ui.number('标签ID', value=0, format='%d').style('width: 80px')
                new_x_input = ui.number('X (m)', value=0.0, step=0.1, format='%.3f').style('width: 100px')
                new_y_input = ui.number('Y (m)', value=0.0, step=0.1, format='%.3f').style('width: 100px')
                new_angle_input = ui.number('角度 (度)', value=0.0, step=15, format='%.1f').style('width: 100px')
            
            def add_tag():
                try:
                    tag_id = int(new_id_input.value)
                    x = new_x_input.value
                    y = new_y_input.value
                    angle = np.radians(new_angle_input.value)
                    
                    robot_localizer.add_field_tag(tag_id, x, y, angle)
                    robot_localizer.save_config()
                    
                    # 更新表格
                    tag_table_data.append({
                        'id': tag_id,
                        'x': f'{x:.3f}',
                        'y': f'{y:.3f}',
                        'angle': f'{np.degrees(angle):.1f}°'
                    })
                    tag_table.update()
                    
                    ui.notify(f'标签 {tag_id} 已添加', type='positive')
                    
                    # 清空输入
                    new_id_input.value = tag_id + 1
                    new_x_input.value = 0.0
                    new_y_input.value = 0.0
                    new_angle_input.value = 0.0
                    
                except Exception as e:
                    logger.error(f"添加标签失败: {e}")
                    ui.notify(f'添加标签失败: {e}', type='negative')
            
            def clear_all_tags():
                robot_localizer.field_tags.clear()
                robot_localizer.save_config()
                tag_table_data.clear()
                tag_table.update()
                ui.notify('所有标签已清除', type='positive')
            
            with ui.row().classes('q-gutter-sm'):
                ui.button('添加标签', on_click=add_tag, color='primary')
                ui.button('清除所有', on_click=clear_all_tags, color='negative')
    
    # 底部：定位状态显示
    with ui.card().classes('q-pa-md q-mt-md').style('width: 100%'):
        ui.markdown('## 定位状态')
        
        status_label = ui.label('定位状态: 未知').classes('text-h6')
        position_label = ui.label('位置: --').classes('text-body1')
        uncertainty_label = ui.label('不确定性: --').classes('text-body1')
        
        def update_localization_status():
            """更新定位状态显示"""
            try:
                from vision.localization import update_localization_from_cameras
                position = update_localization_from_cameras()
                
                if position:
                    x, y, theta = position
                    status_label.text = '定位状态: 正常'
                    position_label.text = f'位置: ({x:.3f}, {y:.3f}) m, 朝向: {np.degrees(theta):.1f}°'
                    
                    # 获取不确定性估计
                    uncertainty = robot_localizer.get_position_uncertainty([])
                    if uncertainty:
                        ux, uy, utheta = uncertainty
                        uncertainty_label.text = f'不确定性: ±{ux:.3f}m, ±{np.degrees(utheta):.1f}°'
                    else:
                        uncertainty_label.text = '不确定性: --'
                else:
                    status_label.text = '定位状态: 无信号'
                    position_label.text = '位置: --'
                    uncertainty_label.text = '不确定性: --'
                    
            except Exception as e:
                status_label.text = f'定位状态: 错误 - {e}'
                logger.error(f"更新定位状态失败: {e}")
        
        # 定时更新状态
        ui.timer(2.0, update_localization_status)  # 每2秒更新一次
        
        with ui.row().classes('q-gutter-md q-mt-md'):
            ui.button('手动更新定位', on_click=update_localization_status, color='primary')
            ui.button('重置定位', on_click=lambda: setattr(robot_localizer, 'last_position', None), color='secondary')
    
    # 添加可视化区域（简单的2D图）
    with ui.card().classes('q-pa-md q-mt-md').style('width: 100%'):
        ui.markdown('## 场地布局可视化')
        
        # 创建一个简单的SVG可视化
        svg_content = '''
        <svg width="400" height="300" viewBox="-1 -1 5 4" style="border: 1px solid #ccc; background: #f9f9f9;">
            <!-- 坐标轴 -->
            <line x1="0" y1="0" x2="4" y2="0" stroke="#ccc" stroke-width="0.02"/>
            <line x1="0" y1="0" x2="0" y2="3" stroke="#ccc" stroke-width="0.02"/>
            
            <!-- 网格 -->
            <defs>
                <pattern id="grid" width="0.5" height="0.5" patternUnits="userSpaceOnUse">
                    <path d="M 0.5 0 L 0 0 0 0.5" fill="none" stroke="#eee" stroke-width="0.01"/>
                </pattern>
            </defs>
            <rect width="4" height="3" fill="url(#grid)"/>
            
            <!-- 这里可以动态添加标签和机器人位置 -->
            <text x="4.1" y="0.1" font-size="0.1" fill="#666">X</text>
            <text x="0.1" y="3.1" font-size="0.1" fill="#666">Y</text>
        </svg>
        '''
        
        ui.html(svg_content)
        ui.label('蓝色圆圈: AprilTag位置, 红色箭头: 小车位置和朝向').classes('text-caption')
