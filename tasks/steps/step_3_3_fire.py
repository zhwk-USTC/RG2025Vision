from typing import Optional
from ..behaviors import set_fire_speed, fire_once, wait_for_ack

class Step33Fire:
    """设置发射速度并触发发射"""
    def __init__(self, velocity: float):
        self.velocity = velocity

    def run(self) -> bool:
        shooter_speed = self.velocity
        set_fire_speed(shooter_speed)
        seq = fire_once()
        wait_for_ack(seq)
        return True