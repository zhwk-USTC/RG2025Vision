from typing import Optional
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
from ..debug_vars_enhanced import set_debug_var, set_debug_image, DebugLevel, DebugCategory
from .utils import align_to_apriltag
import time

FIRESPOT_TAG_ID = 1  # 发射架的 AprilTag ID


class Step31MoveFire:
    """用 AprilTag 位姿闭环，让底盘移动到发射架的指定位置"""

    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = FIRESPOT_TAG_ID, keep_dist: float = 0.8):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.keep_dist = keep_dist

    def run(self) -> bool:
        return align_to_apriltag(
            cam_key=self.cam_key,  # type: ignore
            target_tag_families='tag36h11',
            target_tag_id=self.tag_id,
            target_z=self.keep_dist,
            debug_prefix="firespot_align",
            task_name="MoveToFirespot"
        )

