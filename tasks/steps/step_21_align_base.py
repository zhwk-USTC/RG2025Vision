from typing import Optional
from core.logger import logger
from .utils import align_to_apriltag

TAG_ID = None  # 检测最左边的飞镖，不限定ID


class Step21AlignBase:
    """
    底盘对齐到最左边的飞镖 - 使用tag25h9检测
    """
    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = TAG_ID, keep_dist: float = 0.5):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.keep_dist = keep_dist

    def run(self) -> bool:
        """
        使用tag25h9检测飞镖并对齐
        飞镖在车的左侧，使用'left'摄像头识别
        """
        return align_to_apriltag(
            cam_key=self.cam_key,  # type: ignore
            target_tag_families='tag25h9',
            target_tag_id=self.tag_id,
            target_z=self.keep_dist,
            debug_prefix='align_base',
            task_name='AlignToDart',
            target_x=0.0,
            target_yaw=0.0
        )
