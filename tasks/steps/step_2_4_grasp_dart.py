from ..behaviors import gripper_grasp

class Step24GraspDart:
    """机械臂对齐到飞镖位置"""
    def __init__(self):
        pass

    def run(self) -> bool:
        gripper_grasp()
        return True
