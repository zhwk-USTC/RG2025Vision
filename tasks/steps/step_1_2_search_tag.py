from typing import Optional
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
import time
from vision import get_vision

TAG_ID = 0  # 你要追踪的 AprilTag ID

class Step12SearchTag:
    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = TAG_ID, search_yaw: float = 0.5):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.search_yaw = search_yaw
        
    def run(self) -> bool:
        return True