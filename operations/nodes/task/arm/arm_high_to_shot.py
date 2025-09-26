from ....utils.communicate_utils import (
    arm_reset_to_high_prepare,
    arm_high_prepare_to_grip,
    arm_high_grip_to_shot,
    arm_shot_to_reset
)

class ArmHighToShot:
    def __init__(self):
        pass

    def run(self) -> bool:
        try:
            arm_reset_to_high_prepare()
            arm_high_prepare_to_grip()
            arm_high_grip_to_shot()
            arm_shot_to_reset()
            return True
        except Exception:
            return False