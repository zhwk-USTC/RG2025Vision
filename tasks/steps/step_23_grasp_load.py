from ..behaviors import gripper_grasp_dart, gripper_load_dart, gripper_ready


class Step23GraspLoad:
    """机械臂抓取并装载飞镖"""

    def __init__(self):
        pass

    def run(self) -> bool:
        gripper_ready()
        gripper_grasp_dart()
        gripper_load_dart()
        return True
