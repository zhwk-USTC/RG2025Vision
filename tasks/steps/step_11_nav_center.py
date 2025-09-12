# tasks/step_1_1_align_center.py
from time import sleep
from core.logger import logger
from ..behaviors import base_move
from ..debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

MOVE_FORWARD_M = 1.0
MOVE_LEFT_M = 1.0

class Step11NavCenter:
    """
    开环靠近中间区域
    - 仅向下位机发送位置指令
    """

    def __init__(
        self,
        move_forward: float = MOVE_FORWARD_M,      # m
        move_left: float = MOVE_LEFT_M,         # m
    ) -> None:
        self.move_forward = move_forward
        self.move_left = move_left

    def run(self) -> bool:
        logger.info(
            f"[AlignCenter] 开始开环移动"
        )
        try:
            set_debug_var('nav_center_forward', self.move_forward, DebugLevel.INFO, DebugCategory.CONTROL, "设置向前移动距离")
            set_debug_var('nav_center_left', self.move_left, DebugLevel.INFO, DebugCategory.CONTROL, "设置向左移动距离")
            base_move(self.move_forward, self.move_left, wait_ack=True)
            set_debug_var('nav_center_ack', True, DebugLevel.SUCCESS, DebugCategory.STATUS, "移动指令确认完成")
        except Exception as e:
            logger.error(f"[AlignCenter] 执行异常：{e}")
            set_debug_var('nav_center_error', str(e), DebugLevel.ERROR, DebugCategory.ERROR, "导航到中心区域时发生错误")
            return False
        return True
