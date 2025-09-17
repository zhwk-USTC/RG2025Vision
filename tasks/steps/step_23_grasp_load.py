from ..behaviors import arm_reset, arm_reset_to_prepare, arm_grasp_dart, arm_load_dart, wait_for_ack


class Step23GraspLoad:
    """机械臂抓取并装载飞镖"""

    def __init__(self):
        pass

    def run(self) -> bool:
        arm_reset()
        arm_reset_to_prepare()
        arm_grasp_dart()
        arm_load_dart()
        return True
