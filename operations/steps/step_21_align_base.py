from typing import Optional
from core.logger import logger
from ..utils import base_align_to_apriltag

TAG_ID = None  # 检测最左边的飞镖，不限定ID

TARGET_Z = -0.27

TARGET_X = -0.05

class Step21AlignBase:
    """
    底盘对齐到最左边的飞镖 - 使用tag25h9检测
    """
    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = TAG_ID, target_z: float = TARGET_Z, target_x: float = TARGET_X):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.target_x = target_x
        self.target_z = target_z


    def run(self) -> bool:
        """
        使用tag25h9检测飞镖并对齐
        飞镖在车的左侧，使用'left'摄像头识别
        """
        return base_align_to_apriltag(
            cam_key=self.cam_key,  # type: ignore
            target_tag_families='tag25h9',
            target_tag_id=self.tag_id,
            target_z=self.target_z,
            debug_prefix='align_base',
            task_name='AlignToDart',
            target_x=self.target_x,
        )

