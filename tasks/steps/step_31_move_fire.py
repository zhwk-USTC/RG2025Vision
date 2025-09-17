from typing import Optional
from .utils import base_align_to_apriltag
from core.config.field_config import get_firespot_tag_id, get_current_field
import time

class Step31MoveFire:
    """用 AprilTag 位姿闭环，让底盘移动到发射架的指定位置"""

    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = None, keep_dist: float = 0.8):
        self.cam_key = cam_key
        # 如果没有指定tag_id，从场地配置中获取
        self.tag_id = tag_id if tag_id is not None else get_firespot_tag_id()
        self.keep_dist = keep_dist

    def run(self) -> bool:
        # 获取当前场地信息用于调试
        current_field = get_current_field()
        print(f"[MoveFire] 当前场地: {current_field.name}, 发射架Tag ID: {self.tag_id}")
        
        return base_align_to_apriltag(
            cam_key=self.cam_key,  # type: ignore
            target_tag_families='tag36h11',
            target_tag_id=self.tag_id,
            target_z=self.keep_dist,
            debug_prefix="firespot_align",
            task_name="MoveToFirespot"
        )

