from ..behaviors import send_gripper_tag_pos
from ..debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class Step22AlignArm:
    """机械臂对齐到飞镖位置"""
    def __init__(self):
        pass

    def run(self) -> bool:
        return True
