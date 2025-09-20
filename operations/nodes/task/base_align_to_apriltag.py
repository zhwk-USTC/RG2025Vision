from typing import Optional
from ...utils import base_align_to_apriltag

class BaseAlignToAprilTag:
    """用 AprilTag 位姿闭环，让底盘移动到飞镖架下方并保持距离"""

    def __init__(self, cam_key: str, tag_id: int, target_z: float, target_x: float):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.target_x = target_x
        self.target_z = target_z

    def run(self) -> bool:
        return base_align_to_apriltag(
            cam_key=self.cam_key,  # type: ignore
            target_tag_families='tag36h11',
            target_tag_id=self.tag_id,
            target_z=self.target_z,
            debug_prefix="tag_align",
            task_name="AlignStand",
            target_x=self.target_x,
        )