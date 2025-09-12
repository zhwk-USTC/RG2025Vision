from typing import Optional
from vision import get_vision
from core.logger import logger
from ..behaviors import base_move, base_rotate
from ..debug_vars_enhanced import set_debug_var, set_debug_image, DebugLevel, DebugCategory
import time

TAG_ID = 0  # 你要追踪的 AprilTag ID


class Step12AlignStand:
    """用 AprilTag 位姿闭环，让底盘移动到飞镖架下方并保持距离"""

    def __init__(self, cam_key: str = "left", tag_id: Optional[int] = TAG_ID, keep_dist: float = 0.6):
        self.cam_key = cam_key
        self.tag_id = tag_id
        self.keep_dist = keep_dist

    def _locate_pose(self, vs, frame):
        """
        获取标签位姿的封装函数
        
        Args:
            vs: 视觉系统实例
            frame: 输入图像帧
            
        Returns:
            pose: 标签位姿对象，包含x,y,yaw等信息
            None: 未检测到标签或无法定位
        """
        set_debug_image('tag_align_frame', frame, "对齐飞镖架时的相机帧")
        intr = vs.get_camera_intrinsics(self.cam_key)  # type: ignore
        dets = vs.detect_tag36h11(frame, intr)
        set_debug_var('tag_align_detections', len(dets) if dets else 0, DebugLevel.INFO, DebugCategory.DETECTION, "检测到的标签数量")
        
        if not dets:
            return None
            
        # 选择目标标签
        det = dets[0] if self.tag_id is None else next(
            (d for d in dets if d.tag_id == self.tag_id), dets[0])
        set_debug_var('tag_align_tag_id', getattr(det, 'tag_id', None), DebugLevel.INFO, DebugCategory.DETECTION, "当前检测到的标签ID")

        # 获取位姿
        pose = vs.locate_from_tag(det)
        return pose

    def run(self) -> bool:
        vs = get_vision()
        if not vs:
            set_debug_var('tag_align_error', 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return False
        iter_cnt = 0
        while True:
            frame = vs.read_frame(self.cam_key)  # type: ignore
            if frame is None:
                set_debug_var('tag_align_error', 'empty frame', DebugLevel.ERROR, DebugCategory.ERROR, "无法获取相机帧")
                return False
                
            # 使用封装的函数获取标签位姿
            pose = self._locate_pose(vs, frame)
            if pose is None:
                if iter_cnt > 20:
                    logger.error("[AlignStand] 未检测到飞镖架标签")
                    set_debug_var('tag_align_error', 'no tag found', DebugLevel.ERROR, DebugCategory.DETECTION, "未检测到目标标签")
                    return False
                iter_cnt += 1
                time.sleep(0.05)
                continue

            # 计算误差
            e_x = pose.x - self.keep_dist
            e_y = pose.y
            e_yaw = pose.yaw
            set_debug_var('tag_align_err', {'ex': round(e_x,3), 'ey': round(e_y,3), 'eyaw': round(e_yaw,3)}, DebugLevel.INFO, DebugCategory.POSITION, "与目标位置的误差")
            
            # 判断是否到达目标位置
            if abs(e_x) < 0.05 and abs(e_y) < 0.05 and abs(e_yaw) < 0.1:
                logger.info("[AlignStand] 已对齐到飞镖架")
                set_debug_var('tag_align_status', 'done', DebugLevel.SUCCESS, DebugCategory.STATUS, "已成功对齐到飞镖架")
                break
                
            # 执行移动
            base_move(e_x, -e_y)
            base_rotate(-e_yaw)
            set_debug_var('tag_align_status', 'adjusting', DebugLevel.INFO, DebugCategory.STATUS, "正在调整位置对齐")
            time.sleep(0.05)

        return True
