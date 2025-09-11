from typing import Optional
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
import time

TAG_ID = 0  # 你要追踪的 AprilTag ID


class Step13TagAlign:
    """用 AprilTag 位姿闭环，让底盘移动到飞镖架下方并保持距离"""

    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = TAG_ID, keep_dist: float = 0.6):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.keep_dist = keep_dist

    def run(self) -> bool:
        vs = get_vision()
        while True:
            frame = vs.read_frame(self.cam_key)  # type: ignore
            intr = vs.get_camera_intrinsics(self.cam_key)  # type: ignore
            dets = vs.detect_tag36h11(frame, intr)
            if not dets:
                logger.error("[MoveToTag] 未检测到任何 Tag")
                return False
            det = dets[0] if self.tag_id is None else next(
                (d for d in dets if d.tag_id == self.tag_id), dets[0])

            pose = vs.locate_from_tag(det)
            if pose is None:
                logger.error("[MoveToTag] 无法从 Tag 中定位")
                return False
            e_x = pose.x - self.keep_dist
            e_y = pose.y
            e_yaw = pose.yaw
            if abs(e_x) < 0.05 and abs(e_y) < 0.05 and abs(e_yaw) < 0.1:
                logger.info("[MoveToTag] 已到达目标位置")
                break
            base_move(e_x, -e_y)
            base_rotate(-e_yaw)

        return True
