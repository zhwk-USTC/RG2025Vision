from typing import Optional
from vision import get_vision
from core.logger import logger
from .utils import base_align_to_apriltag
import time

TAG_ID = 5  # 你要追踪的 AprilTag ID

TARGET_Z = 0.5  # 你想保持的距离，单位：米
TARGET_X = 0.0  # 你想保持的侧向位置，单位：米


class Step12AlignStand:
    """用 AprilTag 位姿闭环，让底盘移动到飞镖架下方并保持距离"""

    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = TAG_ID, target_z: float = TARGET_Z, target_x: float = TARGET_X):
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
