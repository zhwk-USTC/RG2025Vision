from ....utils.communicate_utils import arm_reset

class ArmReset:
    def __init__(self):
        pass

    def run(self) -> bool:
        try:
            arm_reset()
            return True
        except Exception:
            return False