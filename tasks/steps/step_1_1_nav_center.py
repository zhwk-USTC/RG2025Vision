# tasks/step_1_1_align_center.py
from time import sleep
from core.logger import logger
from ..behaviors import base_move, wait_for_ack
from ..debug_vars import set_debug_var

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
            set_debug_var('nav_center_forward', self.move_forward)
            set_debug_var('nav_center_left', self.move_left)
            seq = base_move(self.move_forward, self.move_left)
            wait_for_ack(seq)
            set_debug_var('nav_center_ack', True)
        except Exception as e:
            logger.error(f"[AlignCenter] 执行异常：{e}")
            set_debug_var('nav_center_error', str(e))
            return False
        return True
