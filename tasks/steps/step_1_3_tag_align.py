from typing import Optional
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
from ..debug_vars import set_debug_var, set_debug_image
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
        if not vs:
            set_debug_var('tag_align_error', 'vision not ready')
            return False
        iter_cnt = 0
        while True:
            frame = vs.read_frame(self.cam_key)  # type: ignore
            if frame is None:
                set_debug_var('tag_align_error', 'empty frame')
                return False
            # 存储当前原始帧（压缩后）
            set_debug_image('tag_align_frame', frame)
            intr = vs.get_camera_intrinsics(self.cam_key)  # type: ignore
            dets = vs.detect_tag36h11(frame, intr)
            set_debug_var('tag_align_detections', len(dets) if dets else 0)
            if not dets:
                if iter_cnt > 20:
                    logger.error("[MoveToTag] 未检测到任何 Tag")
                    set_debug_var('tag_align_error', 'no tag found')
                    return False
                iter_cnt += 1
                time.sleep(0.05)
                continue
            det = dets[0] if self.tag_id is None else next(
                (d for d in dets if d.tag_id == self.tag_id), dets[0])
            set_debug_var('tag_align_tag_id', getattr(det, 'tag_id', None))

            pose = vs.locate_from_tag(det)
            if pose is None:
                logger.error("[MoveToTag] 无法从 Tag 中定位")
                set_debug_var('tag_align_error', 'pose none')
                return False
            e_x = pose.x - self.keep_dist
            e_y = pose.y
            e_yaw = pose.yaw
            set_debug_var('tag_align_err', {'ex': round(e_x,3), 'ey': round(e_y,3), 'eyaw': round(e_yaw,3)})
            if abs(e_x) < 0.05 and abs(e_y) < 0.05 and abs(e_yaw) < 0.1:
                logger.info("[MoveToTag] 已到达目标位置")
                set_debug_var('tag_align_status', 'done')
                break
            base_move(e_x, -e_y)
            base_rotate(-e_yaw)
            set_debug_var('tag_align_status', 'adjusting')
            time.sleep(0.05)

        return True
