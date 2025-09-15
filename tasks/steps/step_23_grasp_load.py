from ..behaviors import gripper_grasp

class Step23GraspLoad:
    """机械臂抓取并装载飞镖"""
    def __init__(self):
        pass

    def run(self) -> bool:
        gripper_grasp()
        return True
