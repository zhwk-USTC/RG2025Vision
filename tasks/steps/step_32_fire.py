from typing import Optional
from ..behaviors import set_fire_speed
from ..debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory

class Step32Fire:
    """发射"""
    def __init__(self):
        pass
    def run(self) -> Optional[float]:
        shooter_speed = 12.3
        self.velocity = shooter_speed
        set_debug_var('target_prep_speed', shooter_speed, DebugLevel.INFO, DebugCategory.CONTROL, "目标发射速度准备完成")
        
        
        shooter_speed = self.velocity
        set_debug_var('fire_speed_set', shooter_speed, DebugLevel.INFO, DebugCategory.CONTROL, "发射速度已设置")
        set_fire_speed(shooter_speed)
        set_debug_var('fire_done', True, DebugLevel.SUCCESS, DebugCategory.STATUS, "发射完成")
        return shooter_speed
