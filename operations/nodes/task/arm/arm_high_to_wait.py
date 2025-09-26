from ....utils.communicate_utils import (
    arm_reset_to_high_prepare,
    arm_high_prepare_to_grip,
    arm_high_grip_to_wait_shot
)

class ArmHighToWait:
    def __init__(self):
        pass

    def run(self) -> bool:
        try:
            arm_reset_to_high_prepare()
            arm_high_prepare_to_grip()
            arm_high_grip_to_wait_shot()
            return True
        except Exception:
            return False