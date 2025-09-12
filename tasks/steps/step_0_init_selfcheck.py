from time import time, sleep
from typing import Optional
from vision import get_vision
from core.logger import logger
from ..debug_vars import reset_debug_vars

class Step0InitSelfcheck:
    """
    Step 0: 初始化与自检
    - 上位机与下位机握手
    """
    def __init__(self):
        pass

    def run(self) -> bool:
        reset_debug_vars()
        return True