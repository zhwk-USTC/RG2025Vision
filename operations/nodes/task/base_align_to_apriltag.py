from typing import Optional, List
from ...utils.base_alignment_utils import base_align_to_apriltag, DEFAULT_TOLERANCE_XY, DEFAULT_TOLERANCE_YAW
import ast

class BaseAlignToAprilTag:
    """用 AprilTag 位姿闭环，让底盘移动到飞镖架下方并保持距离"""

    def __init__(self, 
                 cam_key: str = 'left', 
                 tag_families: str = 'tag36h11',
                 tag_ids: Optional[List[int]] = None,
                 tag_size: float = 0.12,
                 target_z: float = -1.0, 
                 target_x: float = 0.0,
                 target_yaw: float = 0.0,
                 tolerance_x: float = DEFAULT_TOLERANCE_XY,
                 tolerance_z: float = DEFAULT_TOLERANCE_XY,
                 tolerance_yaw: float = DEFAULT_TOLERANCE_YAW
                 ):
        # 归一化：确保 tag_ids 是 List[int] 或 None
        if tag_ids is not None:
            try:
                # 如果是字符串，尝试解析为列表
                if isinstance(tag_ids, str):
                    tag_ids = ast.literal_eval(tag_ids)
                # 确保是列表，并转换为 int
                if isinstance(tag_ids, list):
                    tag_ids = [int(x) for x in tag_ids]
                    if len(tag_ids) == 0:
                        tag_ids = None
                else:
                    tag_ids = None
            except Exception:
                tag_ids = None

        self.cam_key = cam_key
        self.tag_families = tag_families
        self.tag_ids = tag_ids
        self.tag_size = tag_size
        self.target_x = target_x
        self.target_z = target_z
        self.target_yaw = target_yaw
        self.tolerance_x = tolerance_x
        self.tolerance_z = tolerance_z
        self.tolerance_yaw = tolerance_yaw

    def run(self) -> bool:
        return base_align_to_apriltag(
            cam_key=self.cam_key,  # type: ignore
            target_tag_families=self.tag_families,
            target_tag_ids=self.tag_ids,
            target_tag_size=self.tag_size,
            target_z=self.target_z,
            target_x=self.target_x,
            target_yaw=self.target_yaw,
            tolerance_x=self.tolerance_x,
            tolerance_z=self.tolerance_z,
            tolerance_yaw=self.tolerance_yaw
        )
