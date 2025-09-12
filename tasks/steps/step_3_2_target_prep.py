from typing import Optional
from ..behaviors import set_fire_speed, fire_once, wait_for_ack
from ..debug_vars import set_debug_var

class Step32Fire:
    """根据目标距离解算发射速度"""
    def __init__(self):
        pass
    def run(self) -> Optional[float]:
        shooter_speed = 12.3
        self.velocity = shooter_speed
        set_debug_var('target_prep_speed', shooter_speed)
        
        
        shooter_speed = self.velocity
        set_debug_var('fire_speed_set', shooter_speed)
        set_fire_speed(shooter_speed)
        seq = fire_once()
        set_debug_var('fire_seq', seq)
        wait_for_ack(seq)
        set_debug_var('fire_done', True)
        return shooter_speed
