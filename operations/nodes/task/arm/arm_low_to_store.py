from ....utils.communicate_utils import (
    arm_reset_to_store,
    arm_store_to_reset
)

class ArmLowToStore:
    def __init__(self):
        pass

    def run(self) -> bool:
        try:
            arm_reset_to_store()
            arm_store_to_reset()
            return True
        except Exception:
            return False