from typing import Optional
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
import time
from vision import get_vision
from ..debug_vars import set_debug_var, set_debug_image

TAG_ID = 0  # 你要追踪的 AprilTag ID

class Step12SearchTag:
    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = TAG_ID, search_yaw: float = 0.5):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.search_yaw = search_yaw
        
    def run(self) -> bool:
        # 测试：生成一张空（黑色）图片并上传到 debug vars
        try:
            import numpy as np  # type: ignore
            import cv2  # type: ignore
            img = np.zeros((180, 240, 3), dtype=np.uint8)
            cv2.putText(img, 'EMPTY', (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2, cv2.LINE_AA)
            ok = set_debug_image('search_tag_test_image', img)
            set_debug_var('search_tag_image_ok', ok)
        except Exception as e:
            set_debug_var('search_tag_image_error', str(e))
            return False
        set_debug_var('search_tag_status', 'image_test_done')
        return True