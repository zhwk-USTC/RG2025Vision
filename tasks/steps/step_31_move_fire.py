from typing import Optional
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
from ..debug_vars_enhanced import set_debug_var, set_debug_image, DebugLevel, DebugCategory
import time

FIRESPOT_TAG_ID = 1  # 发射架的 AprilTag ID


class Step31MoveFire:
    """用 AprilTag 位姿闭环，让底盘移动到发射架的指定位置"""

    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = FIRESPOT_TAG_ID, keep_dist: float = 0.8):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.keep_dist = keep_dist

    def run(self) -> bool:
        vs = get_vision()
        if not vs:
            set_debug_var('firespot_align_error', 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return False
        iter_cnt = 0
        while True:
            frame = vs.read_frame(self.cam_key)  # type: ignore
            if frame is None:
                set_debug_var('firespot_align_error', 'empty frame', DebugLevel.ERROR, DebugCategory.ERROR, "无法获取相机帧")
                return False
            # 存储当前原始帧（压缩后）
            set_debug_image('firespot_align_frame', frame, "对齐发射位置时的相机帧")
            intr = vs.get_camera_intrinsics(self.cam_key)  # type: ignore
            dets = vs.detect_tag36h11(frame, intr)
            set_debug_var('firespot_align_detections', len(dets) if dets else 0, DebugLevel.INFO, DebugCategory.DETECTION, "检测到的发射架标签数量")
            if not dets:
                if iter_cnt > 20:
                    logger.error("[MoveToFirespot] 未检测到发射架 Tag")
                    set_debug_var('firespot_align_error', 'no firespot tag found', DebugLevel.ERROR, DebugCategory.DETECTION, "未检测到发射架标签")
                    return False
                iter_cnt += 1
                time.sleep(0.05)
                continue
            det = dets[0] if self.tag_id is None else next(
                (d for d in dets if d.tag_id == self.tag_id), dets[0])
            set_debug_var('firespot_align_tag_id', getattr(det, 'tag_id', None), DebugLevel.INFO, DebugCategory.DETECTION, "当前检测到的发射架标签ID")

            pose = vs.locate_from_tag(det)
            if pose is None:
                logger.error("[MoveToFirespot] 无法从发射架 Tag 中定位")
                set_debug_var('firespot_align_error', 'pose none', DebugLevel.ERROR, DebugCategory.POSITION, "无法从标签获取位姿信息")
                return False
            e_x = pose.x - self.keep_dist
            e_y = pose.y
            e_yaw = pose.yaw
            set_debug_var('firespot_align_err', {'ex': round(e_x,3), 'ey': round(e_y,3), 'eyaw': round(e_yaw,3)}, DebugLevel.INFO, DebugCategory.POSITION, "与发射位置的误差")
            if abs(e_x) < 0.05 and abs(e_y) < 0.05 and abs(e_yaw) < 0.1:
                logger.info("[MoveToFirespot] 已到达发射位置")
                set_debug_var('firespot_align_status', 'done', DebugLevel.SUCCESS, DebugCategory.STATUS, "已成功到达发射位置")
                break
            base_move(e_x, -e_y)
            base_rotate(-e_yaw)
            set_debug_var('firespot_align_status', 'adjusting', DebugLevel.INFO, DebugCategory.STATUS, "正在调整位置到发射点")
            time.sleep(0.05)

        return True

