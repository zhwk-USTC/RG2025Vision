from typing import Any
from ..debug_vars import set_debug_var

class Step22AlignBase:
    """
    底盘对齐到飞镖
    """
    def __init__(self):
        pass

    def run(self) -> bool:
        set_debug_var('align_base_status', 'aligned')
        return True
