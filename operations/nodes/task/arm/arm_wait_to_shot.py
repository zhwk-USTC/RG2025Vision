from ....utils.communicate_utils import arm_wait_shot_to_shot, arm_shot_to_reset

class ArmWaitToShot:
    def __init__(self):
        pass

    def run(self) -> bool:
        try:
            arm_wait_shot_to_shot()
            arm_shot_to_reset()
            return True
        except Exception:
            return False