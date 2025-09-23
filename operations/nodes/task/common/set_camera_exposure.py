from typing import Literal, cast
from vision import CAM_KEY_TYPE
from core.logger import logger
from operations.debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory
from operations.utils.vision_utils import VisionUtils

class SetCameraExposure:
    """
    设置摄像头曝光时间
    """
    def __init__(self, cam_key: str, exposure_raw: float):
        self.cam_key = cam_key
        self.exposure_raw = exposure_raw

    def run(self) -> bool:
        logger.info(f"[SetCameraExposure] 设置摄像头 {self.cam_key} 曝光时间为 {self.exposure_raw}")
        set_debug_var('set_exposure_start', f'{self.cam_key}:{self.exposure_raw}',
                      DebugLevel.INFO, DebugCategory.STATUS, f"开始设置摄像头 {self.cam_key} 曝光时间")

        success = VisionUtils.set_cam_exposure(cast(CAM_KEY_TYPE, self.cam_key), self.exposure_raw)

        if success:
            logger.info(f"[SetCameraExposure] 摄像头 {self.cam_key} 曝光时间设置成功")
            set_debug_var('set_exposure_result', 'success',
                          DebugLevel.SUCCESS, DebugCategory.STATUS, f"摄像头 {self.cam_key} 曝光时间设置成功")
        else:
            logger.error(f"[SetCameraExposure] 摄像头 {self.cam_key} 曝光时间设置失败")
            set_debug_var('set_exposure_result', 'failed',
                          DebugLevel.ERROR, DebugCategory.ERROR, f"摄像头 {self.cam_key} 曝光时间设置失败")

        return success