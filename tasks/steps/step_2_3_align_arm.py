from ..behaviors import send_gripper_tag_pos

class Step23AlignArm:
    """机械臂对齐到飞镖位置"""
    def __init__(self):
        pass

    def run(self) -> bool:
        send_gripper_tag_pos(0.1, 0.2, 0.3) 
        return True
