from ..behaviors import send_gripper_tag_pos
from ..debug_vars import set_debug_var

class Step23AlignArm:
    """机械臂对齐到飞镖位置"""
    def __init__(self):
        pass

    def run(self) -> bool:
        x, y, z = 0.1, 0.2, 0.3
        send_gripper_tag_pos(x, y, z)
        set_debug_var('align_arm_target', {'x': x, 'y': y, 'z': z})
        return True
