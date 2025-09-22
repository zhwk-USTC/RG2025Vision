from typing import Optional
from ...utils.turret_alignment_utils import turret_align_front_to_light_column
from ...utils.communicate_utils import set_turret_yaw

class TurretAlignToLight:
    """用 HSV 灯检测，让炮台对准到指定列位置"""

    def __init__(self,
                 cam_key: str = "front",
                 target_column: float = 0.5,         # 0~1 归一化 或 像素列(>1)
                 pixel_tolerance: int = 3,
                 target_hsv_label: Optional[str] = None
                 ):
        self.cam_key = cam_key
        self.target_column = target_column
        self.pixel_tolerance = pixel_tolerance
        self.target_hsv_label = target_hsv_label

    def run(self) -> bool:
        # 先将炮台移动到中间位置0
        set_turret_yaw(0.0)
        
        return turret_align_front_to_light_column(
            cam_key=self.cam_key,  # type: ignore
            target_column=self.target_column,
            pixel_tolerance=self.pixel_tolerance,
            target_hsv_label=self.target_hsv_label,
            start_norm=0.0,
            debug_prefix="turret_align",
            task_name="TurretAlignToLight"
        )