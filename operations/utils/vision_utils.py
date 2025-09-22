
from typing import Optional
import time
from vision import get_vision, CAM_KEY_TYPE
from core.logger import logger
from ..debug_vars_enhanced import set_debug_var, set_debug_image, DebugLevel, DebugCategory


class VisionUtils:
    """视觉相关工具函数"""

    @staticmethod
    def check_vision_system(error_prefix: str = "vision_error") -> bool:
        vs = get_vision()
        if not vs:
            set_debug_var(error_prefix, 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return False
        return True

    @staticmethod
    def get_frame_safely(
        cam_key: CAM_KEY_TYPE,
        error_prefix: str = "frame_error",
        debug_image_key: Optional[str] = None,
        debug_description: str = ""
    ):
        vs = get_vision()
        if not vs:
            return None

        # 检查并连接摄像头
        cam = vs._cameras.get(cam_key)
        if cam is None:
            set_debug_var(error_prefix, 'camera not found', DebugLevel.ERROR, DebugCategory.ERROR, f"未找到摄像头 {cam_key}")
            return None
        
        if not cam.is_open:
            logger.info(f"[VisionUtils] 摄像头 {cam_key} 未连接，正在连接...")
            if not cam.connect():
                set_debug_var(error_prefix, 'camera connect failed', DebugLevel.ERROR, DebugCategory.ERROR, f"摄像头 {cam_key} 连接失败")
                return None
            logger.info(f"[VisionUtils] 摄像头 {cam_key} 连接成功")

        try:
            frame = vs.read_frame(cam_key)  # type: ignore
            if frame is None:
                set_debug_var(error_prefix, 'empty frame', DebugLevel.ERROR, DebugCategory.ERROR, "无法获取相机帧")
                return None

            if debug_image_key:
                set_debug_image(debug_image_key, frame, debug_description)
            return frame
        except RuntimeError as e:
            set_debug_var(error_prefix, f'read frame error: {str(e)}', DebugLevel.ERROR, DebugCategory.ERROR, f"读取相机帧失败: {str(e)}")
            return None

    @staticmethod
    def detect_apriltag_with_retry(
        cam_key: CAM_KEY_TYPE,
        target_tag_families: str,
        target_tag_id: Optional[int] = None,
        max_retries: int = 20,
        retry_delay: float = 0.05,
        debug_prefix: str = "tag",
        debug_description: str = "标签检测"
    ):
        vs = get_vision()
        if not vs:
            set_debug_var(f'{debug_prefix}_error', 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return None, None

        iter_cnt = 0
        while iter_cnt <= max_retries:
            frame = VisionUtils.get_frame_safely(
                cam_key,
                f'{debug_prefix}_error',
                f'{debug_prefix}_frame',
                f"{debug_description}时的相机帧"
            )
            if frame is None:
                return None, None

            intr = vs.get_camera_intrinsics(cam_key)  # type: ignore
            if(target_tag_families == 'tag36h11'):
                dets = vs.detect_tag36h11(frame, intr)
            elif target_tag_families == 'tag25h9':
                dets = vs.detect_tag25h9(frame, intr)
            else:
                set_debug_var(f'{debug_prefix}_error', 'unknown tag family', DebugLevel.ERROR, DebugCategory.ERROR, f"未知的标签族: {target_tag_families}")
                return None, None
            set_debug_var(f'{debug_prefix}_detections', len(dets) if dets else 0,
                          DebugLevel.INFO, DebugCategory.DETECTION, f"检测到的{debug_description}数量")

            if not dets:
                if iter_cnt >= max_retries:
                    logger.error(f"[{debug_description}] 未检测到标签")
                    set_debug_var(f'{debug_prefix}_error', 'no tag found',
                                  DebugLevel.ERROR, DebugCategory.DETECTION, f"未检测到{debug_description}")
                    return None, None
                iter_cnt += 1
                time.sleep(retry_delay)
                continue

            # 选择目标标签：选择最左边的（满足ID条件的）标签
            if target_tag_id is None:
                # 未指定ID时选择最左边的标签（按中心x坐标排序）
                det = min(dets, key=lambda d: getattr(d, 'center', [float('inf'), 0])[0])
            else:
                # 指定了ID时，在满足ID条件的标签中选择最左边的
                matching_dets = [d for d in dets if getattr(d, 'tag_id', None) == target_tag_id]
                if not matching_dets:
                    if iter_cnt >= max_retries:
                        logger.error(f"[{debug_description}] 未找到指定ID={target_tag_id}的标签")
                        set_debug_var(f'{debug_prefix}_error', f'target tag {target_tag_id} not found',
                                      DebugLevel.ERROR, DebugCategory.DETECTION, f"未找到指定{debug_description}ID={target_tag_id}")
                        return None, None
                    iter_cnt += 1
                    time.sleep(retry_delay)
                    continue
                # 在匹配ID的标签中选择最左边的
                det = min(matching_dets, key=lambda d: getattr(d, 'center', [float('inf'), 0])[0])
            set_debug_var(f'{debug_prefix}_tag_id', getattr(det, 'tag_id', None),
                          DebugLevel.INFO, DebugCategory.DETECTION, f"当前检测到的{debug_description}ID")

            pose = vs.locate_from_tag(det)
            if pose is None:
                logger.error(f"[{debug_description}] 无法从标签中定位")
                set_debug_var(f'{debug_prefix}_error', 'pose none',
                              DebugLevel.ERROR, DebugCategory.POSITION, "无法从标签获取位姿信息")
                return None, None

            return det, pose

        return None, None

    @staticmethod
    def detect_hsv_with_retry(
        cam_key: CAM_KEY_TYPE,
        target_label: str,
        max_retries: int = 20,
        interval_sec: float = 0.05,
        debug_prefix: str = "hsv",
        task_name: str = "HSV检测"
    ):
        """
        HSV颜色检测带重试功能
        
        Args:
            cam_key: 摄像头键值
            target_label: 目标HSV标签名称
            max_retries: 最大重试次数
            interval_sec: 重试间隔（秒）
            debug_prefix: 调试变量前缀
            task_name: 任务名称（用于日志）
            
        Returns:
            tuple: (detection_result, None) 如果检测成功，否则 (None, None)
                   detection_result 包含 center 属性表示检测到的中心像素坐标
        """
        vs = get_vision()
        if not vs:
            set_debug_var(f'{debug_prefix}_error', 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return None, None

        iter_cnt = 0
        while iter_cnt <= max_retries:
            frame = VisionUtils.get_frame_safely(
                cam_key,
                f'{debug_prefix}_error',
                f'{debug_prefix}_frame',
                f"{task_name}时的相机帧"
            )
            if frame is None:
                return None, None

            try:
                # 调用视觉系统的HSV检测方法
                dets = vs.detect_hsv(frame)
                
                set_debug_var(f'{debug_prefix}_detections', len(dets) if dets else 0,
                              DebugLevel.INFO, DebugCategory.DETECTION, f"检测到的{task_name}目标数量")

                if not dets:
                    if iter_cnt >= max_retries:
                        logger.error(f"[{task_name}] 未检测到HSV目标: {target_label}")
                        set_debug_var(f'{debug_prefix}_error', f'no hsv target found: {target_label}',
                                      DebugLevel.ERROR, DebugCategory.DETECTION, f"未检测到{task_name}目标")
                        return None, None
                    iter_cnt += 1
                    time.sleep(interval_sec)
                    continue

                # 选择检测结果（通常选择面积最大的或置信度最高的）
                if isinstance(dets, list) and len(dets) > 0:
                    # 选择得分最高的检测结果
                    det = max(dets, key=lambda d: getattr(d, 'score', 0))
                else:
                    det = dets

                set_debug_var(f'{debug_prefix}_center', getattr(det, 'center', None),
                              DebugLevel.INFO, DebugCategory.DETECTION, f"{task_name}检测到的中心坐标")

                return det, None

            except Exception as e:
                logger.error(f"[{task_name}] HSV检测异常: {str(e)}")
                set_debug_var(f'{debug_prefix}_error', f'hsv detection error: {str(e)}',
                              DebugLevel.ERROR, DebugCategory.ERROR, f"{task_name}检测异常")
                if iter_cnt >= max_retries:
                    return None, None
                iter_cnt += 1
                time.sleep(interval_sec)

        return None, None