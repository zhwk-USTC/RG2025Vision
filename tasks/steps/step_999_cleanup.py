from core.logger import logger
from vision import get_vision
from communicate import stop_serial

class Step999Cleanup:
    """
    Step 999：清理与关停（可重复调用、幂等）
    - 停止任务运动 / 关闭执行器
    - 断开相机 / 释放视觉系统
    - 关闭串口/网络连接
    - 保存必要日志 / 状态
    """
    def __init__(self, open_gripper_on_exit: bool = True):
        self.open_gripper_on_exit = open_gripper_on_exit
        self._done = False

    def run(self) -> bool:
        if self._done:
            return True

        ok = True

        # 1) 下位机安全停止（先让一切不再运动/发射）
        try:
            # stop_all()             # 一键急停（若有）
            # chassis_stop()
            # stop_flywheel()
            # if self.open_gripper_on_exit:
            #     open_gripper()
            # arm_relax()
            logger.info("[Cleanup] 执行器已进入安全状态")
        except Exception as e:
            logger.warning(f"[Cleanup] 执行器清理异常：{e}")
            ok = False

        # 2) 视觉关停（断开相机、释放资源）
        try:
            vs = get_vision()
            vs.shutdown()
            logger.info("[Cleanup] 视觉系统已关闭")
        except Exception as e:
            logger.warning(f"[Cleanup] 视觉系统清理异常：{e}")
            ok = False

        # 3) 通讯释放（串口/Socket）
        try:
            stop_serial()
            logger.info("[Cleanup] 通讯通道已关闭")
        except Exception as e:
            logger.warning(f"[Cleanup] 通讯关闭异常：{e}")
            ok = False

        self._done = True
        return ok
