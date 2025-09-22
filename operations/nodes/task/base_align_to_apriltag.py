from typing import Optional
from ...utils.base_alignment_utils import base_align_to_apriltag, DEFAULT_TOLERANCE_XY, DEFAULT_TOLERANCE_YAW

class BaseAlignToAprilTag:
    """用 AprilTag 位姿闭环，让底盘移动到飞镖架下方并保持距离"""

    def __init__(self, 
                 cam_key: str, 
                 tag_id: int, 
                 target_z: float, 
                 target_x: float,
                 target_yaw: float = 0.0,
                 tolerance_x: float = DEFAULT_TOLERANCE_XY,
                 tolerance_z: float = DEFAULT_TOLERANCE_XY,
                 tolerance_yaw: float = DEFAULT_TOLERANCE_YAW
                 ):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.target_x = target_x
        self.target_z = target_z
        self.target_yaw = target_yaw
        self.tolerance_x = tolerance_x
        self.tolerance_z = tolerance_z
        self.tolerance_yaw = tolerance_yaw

    def run(self) -> bool:
        return base_align_to_apriltag(
            cam_key=self.cam_key,  # type: ignore
            target_tag_families='tag36h11',
            target_tag_id=self.tag_id,
            target_z=self.target_z,
            target_x=self.target_x,
            target_yaw=self.target_yaw,
            tolerance_x=self.tolerance_x,
            tolerance_z=self.tolerance_z,
            tolerance_yaw=self.tolerance_yaw
        )