# tasks/step_1_1_align_center.py
import time
from core.logger import logger
from ..utils.communicate_utils import base_move, base_stop
from ..debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

MOVE_FORWARD_TIME = 1.0
MOVE_LEFT_TIME = 1.0

class Step11NavCenter:
    """
    开环靠近中间区域
    - 仅向下位机发送位置指令
    """

    def __init__(
        self,
        move_forward: float = MOVE_FORWARD_TIME,
        move_left: float = MOVE_LEFT_TIME,
    ) -> None:
        self.move_forward = move_forward
        self.move_left = move_left

    def run(self) -> bool:
        logger.info(
            f"[AlignCenter] 开始开环移动"
        )
        try:
            set_debug_var('nav_center_forward', self.move_forward, DebugLevel.INFO, DebugCategory.CONTROL, "设置向前移动时间")
            set_debug_var('nav_center_left', self.move_left, DebugLevel.INFO, DebugCategory.CONTROL, "设置向左移动时间")
            base_move('forward_fast')
            time.sleep(self.move_forward)
            base_stop()
            time.sleep(0.5)
            base_move('left_fast')
            time.sleep(self.move_left)
            base_stop()
        except Exception as e:
            logger.error(f"[AlignCenter] 执行异常：{e}")
            set_debug_var('nav_center_error', str(e), DebugLevel.ERROR, DebugCategory.ERROR, "导航到中心区域时发生错误")
            base_stop()
            return False
        return True
