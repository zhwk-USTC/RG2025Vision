from typing import Optional, Any
from vision import get_vision
from ..debug_vars import set_debug_var

class Step21DetectLeftmostDart:
    """
    检测并返回最左侧飞镖的位置
    """
    def __init__(self):
        pass
    
    def run(self) -> Optional[Any]:
        v = get_vision()
        if not v:
            set_debug_var('detect_leftmost_error', 'vision not ready')
            return None
        # 伪造一个结果
        dart_pos = {'x': 0.1, 'y': 0.2, 'z': 0.0}
        set_debug_var('detect_leftmost_dart', dart_pos)
        return dart_pos
