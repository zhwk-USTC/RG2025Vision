from ....utils.communicate_utils import (
    arm_reset_to_low_prepare,
    arm_low_prepare_to_grip,
    arm_low_grip_to_wait_shot,
)

class ArmLowToWait:
    def __init__(self):
        pass

    def run(self) -> bool:
        try:
            arm_reset_to_low_prepare()
            arm_low_prepare_to_grip()
            arm_low_grip_to_wait_shot()
            return True
        except Exception:
            return False