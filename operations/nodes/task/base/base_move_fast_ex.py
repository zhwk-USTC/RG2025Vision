import time
from core.logger import logger
from ....utils.communicate_utils import base_set_move, base_stop
from ....debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class BaseMoveFastEx:
    """
    底盘快速移动任务
    支持forward_fast_ex和backward_fast_ex移动，带前置缓冲
    """

    def __init__(
        self,
        direction: str = 'forward',
        duration: float = 1.0,
    ) -> None:
        """
        参数：
        - direction: 移动方向 ('forward', 'backward')
        - duration: 移动持续时间（秒）
        """
        if direction not in ['forward', 'backward']:
            raise ValueError("direction must be 'forward' or 'backward'")
        self.direction = direction
        self.duration = duration

    def run(self) -> bool:
        logger.info(f"[BaseMoveFastEx] 开始快速移动: {self.direction}_fast_ex, 持续{self.duration}秒")

        try:
            set_debug_var('base_move_fast_ex_direction', f"{self.direction}_fast_ex",
                         DebugLevel.INFO, DebugCategory.CONTROL, "底盘快速移动方向")
            set_debug_var('base_move_fast_ex_duration', self.duration,
                         DebugLevel.INFO, DebugCategory.CONTROL, "底盘快速移动持续时间")

            slow_command = f"{self.direction}_slow"
            fast_command = f"{self.direction}_fast"
            ex_command = f"{self.direction}_fast_ex"
            base_set_move(slow_command)  # type: ignore
            time.sleep(0.2)
            base_set_move(fast_command)  # type: ignore
            time.sleep(0.3)
            base_set_move(ex_command)  # type: ignore
            time.sleep(self.duration)
            base_set_move(fast_command)  # type: ignore
            time.sleep(0.3)
            base_set_move(slow_command)  # type: ignore
            time.sleep(0.2)

            logger.info("[BaseMoveFastEx] 快速移动完成")
            set_debug_var('base_move_fast_ex_status', 'success',
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "底盘快速移动成功")

        except Exception as e:
            logger.error(f"[BaseMoveFastEx] 快速移动异常：{e}")
            set_debug_var('base_move_fast_ex_error', str(e),
                         DebugLevel.ERROR, DebugCategory.ERROR, "底盘快速移动时发生错误")
            base_stop()
            return False

        return True