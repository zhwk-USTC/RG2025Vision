# tasks/step_1_1_align_center.py
from time import sleep
from core.logger import logger
from ..behaviors import base_move, wait_for_ack

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
            seq = base_move(self.move_forward, self.move_left)
            wait_for_ack(seq)
        except Exception as e:
            logger.error(f"[AlignCenter] 执行异常：{e}")
            return False
        return True
