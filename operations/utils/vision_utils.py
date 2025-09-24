from typing import Optional, List
import time
from vision import get_vision, CAM_KEY_TYPE
from core.logger import logger
from ..debug_vars_enhanced import set_debug_var, set_debug_image, DebugLevel, DebugCategory


class VisionUtils:
    """视觉相关工具函数"""

    # 存储上一个检测到的AprilTag的中心坐标
    _last_tag_center: Optional[List[float]] = None

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
        target_tag_size: Optional[float] = None,
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

            intr = vs.get_camera_intrinsics(cam_key)
            if(target_tag_families == 'tag36h11'):
                dets = vs.detect_tag36h11(frame, intr, target_tag_size)
            elif target_tag_families == 'tag25h9':
                dets = vs.detect_tag25h9(frame, intr, target_tag_size)
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

            # 选择目标标签：选择与上一个返回值距离最近的满足条件的标签
            if target_tag_id is None:
                # 未指定ID时，选择所有检测到的标签
                candidate_dets = dets
            else:
                # 指定了ID时，选择匹配ID的标签
                candidate_dets = [d for d in dets if getattr(d, 'tag_id', None) == target_tag_id]
                if not candidate_dets:
                    if iter_cnt >= max_retries:
                        logger.error(f"[{debug_description}] 未找到指定ID={target_tag_id}的标签")
                        set_debug_var(f'{debug_prefix}_error', f'target tag {target_tag_id} not found',
                                      DebugLevel.ERROR, DebugCategory.DETECTION, f"未找到指定{debug_description}ID={target_tag_id}")
                        return None, None
                    iter_cnt += 1
                    time.sleep(retry_delay)
                    continue

            # 从候选标签中选择一个
            # 仅选择最靠近中间列的标签
            height, width = frame.shape[:2]
            center_x = width / 2
            det = min(candidate_dets, key=lambda d: abs(getattr(d, 'center', [center_x, 0])[0] - center_x))

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
                        logger.error(f"[{task_name}] 未检测到HSV目标")
                        set_debug_var(f'{debug_prefix}_error', 'no hsv target found',
                                      DebugLevel.ERROR, DebugCategory.DETECTION, f"未检测到{task_name}目标")
                        return None, None
                    iter_cnt += 1
                    time.sleep(interval_sec)
                    continue

                # 选择检测结果：选择距离图像中心列最近的
                if isinstance(dets, list) and len(dets) > 0:
                    # 获取图像宽度，计算中心列
                    height, width = frame.shape[:2]
                    center_x = width / 2
                    # 选择距离中心列最近的检测结果
                    det = min(dets, key=lambda d: abs(getattr(d, 'center', [center_x, 0])[0] - center_x))
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
    

    @staticmethod
    def set_cam_exposure(cam_key: CAM_KEY_TYPE, exposure_raw: float) -> bool:
        """设置摄像头曝光时间"""
        vs = get_vision()
        if not vs:
            set_debug_var('vision_error', 'vision not ready', DebugLevel.ERROR, DebugCategory.ERROR, "视觉系统未准备就绪")
            return False

        cam = vs._cameras.get(cam_key)
        if cam is None:
            set_debug_var('camera_error', 'camera not found', DebugLevel.ERROR, DebugCategory.ERROR, f"未找到摄像头 {cam_key}")
            return False
        
        if not cam.is_open:
            logger.info(f"[VisionUtils] 摄像头 {cam_key} 未连接，正在连接...")
            if not cam.connect():
                set_debug_var('camera_error', 'camera connect failed', DebugLevel.ERROR, DebugCategory.ERROR, f"摄像头 {cam_key} 连接失败")
                return False
            logger.info(f"[VisionUtils] 摄像头 {cam_key} 连接成功")

        try:
            cam._config.exposure = exposure_raw
            cam._set_exposure_smart()
            logger.info(f"[VisionUtils] 摄像头 {cam_key} 曝光时间设置为 {exposure_raw}")
            return True
        except Exception as e:
            set_debug_var('camera_error', f'set exposure error: {str(e)}', DebugLevel.ERROR, DebugCategory.ERROR, f"设置摄像头 {cam_key} 曝光时间异常: {str(e)}")
            return False