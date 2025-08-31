"""
定位配置界面
"""

from typing import List, Dict
import numpy as np
from PIL import Image
from nicegui import ui
from core.logger import logger
from vision import localizer
# ---------------------------
# 常量 / 工具
# ---------------------------
def _deg(rad: float) -> float:
    try:
        return float(np.degrees(rad))
    except Exception:
        return 0.0


# ---------------------------
# 组件渲染
# ---------------------------

composed_field_image_widget= []

def _render_field_map_card() -> None:
    with ui.card().classes("q-pa-md q-mb-md").style("width: 100%"):
        ui.markdown("## 场地可视化")
        composed_field_image_widget.append(ui.interactive_image())
    ui.label(f'当前位置朝向：{localizer.last_pose}')

def _update_composed_field_image() -> None:
    composed_field_image_widget[0].set_source(localizer.compose_visible_field())

def _render_camera_pose_card() -> None:
    with ui.card().classes("q-pa-md q-mb-md").style("width: 100%"):
        ui.markdown("## 摄像头位置（只读）")
        poses = getattr(localizer, "camera_poses", []) or []
        if not poses:
            ui.label("未检测到摄像头位姿数据").classes("text-negative")
            return

        with ui.row().classes("q-gutter-md"):
            for i, pose in enumerate(poses):
                with ui.column().classes("q-gutter-sm").style("flex: 1; min-width: 220px"):
                    ui.label(f"摄像头 {i}").classes("text-h6 text-center")
                    ui.number("X 坐标 (m)", value=float(pose.x), format="%.3f") \
                        .classes("w-full").props("readonly")
                    ui.number("Y 坐标 (m)", value=float(pose.y), format="%.3f") \
                        .classes("w-full").props("readonly")
                    ui.number("角度 (rad)", value=_deg(float(pose.yaw)), format="%.1f") \
                        .classes("w-full").props("readonly")


def _render_tag_table_card() -> None:
    with ui.card().classes("q-pa-md q-mb-md").style("width: 100%"):
        ui.markdown("## 场地 AprilTag 配置（只读）")
        rows: List[Dict] = []
        field_tags = getattr(localizer, "field_tags", {}) or {}
        for tag_id, tag in field_tags.items():
            rows.append({
                "id": tag_id,
                "x": f"{float(tag.x):.3f}",
                "y": f"{float(tag.y):.3f}",
                "yaw": f"{_deg(float(tag.yaw)):.1f}°",
            })

        ui.table(
            columns=[
                {"name": "id", "label": "ID", "field": "id"},
                {"name": "x", "label": "X (m)", "field": "x"},
                {"name": "y", "label": "Y (m)", "field": "y"},
                {"name": "yaw", "label": "角度 (rad)", "field": "yaw"},
            ],
            rows=rows,
        ).classes("w-full")


# ---------------------------
# 外部入口
# ---------------------------

def render_localization_page() -> None:
    ui.markdown("# 定位配置")
    _render_field_map_card()
    _render_camera_pose_card()
    _render_tag_table_card()
    
    ui.timer(1.0/5, _update_composed_field_image)
