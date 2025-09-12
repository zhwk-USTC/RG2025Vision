import threading
import time
from .steps.step_0_init_selfcheck import Step0InitSelfcheck
from .steps.step_1_1_nav_center import Step11NavCenter
from .steps.step_1_2_search_tag import Step12SearchTag
from .steps.step_1_3_tag_align import Step13TagAlign
from .steps.step_2_1_detect_leftmost import Step21DetectLeftmostDart
from .steps.step_2_2_align_base import Step22AlignBase
from .steps.step_2_3_align_arm import Step23AlignArm
from .steps.step_2_4_grasp_dart import Step24GraspDart
from .steps.step_2_5_load_dart import Step25LoadDart
from .steps.step_3_1_to_firespot import Step31ToFirespot
from .steps.step_3_2_target_prep import Step32Fire
from .steps.step_999_cleanup import Step999Cleanup
from .debug_vars import reset_debug_vars, set_debug_var

_STEP_CLASSES = {
    "Step11NavCenter": Step11NavCenter,
    "Step12SearchTag": Step12SearchTag,
    "Step13TagAlign": Step13TagAlign,
    "Step21DetectLeftmostDart": Step21DetectLeftmostDart,
    "Step22AlignBase": Step22AlignBase,
    "Step23AlignArm": Step23AlignArm,
    "Step24GraspDart": Step24GraspDart,
    "Step25LoadDart": Step25LoadDart,
    "Step31ToFirespot": Step31ToFirespot,
    "Step32Fire": Step32Fire,
}

def run_step(step_name: str):
    """同步执行（阻塞）一个步骤，主要用于脚本调用。"""
    step_cls = _STEP_CLASSES.get(step_name)
    if not step_cls:
        return False
    reset_debug_vars()
    set_debug_var('current_step', step_name)
    set_debug_var('status', 'init')
    step0 = Step0InitSelfcheck()
    step999 = Step999Cleanup()
    try:
        set_debug_var('status', 'selfcheck')
        step0.run()
        step = step_cls()  # 若需要参数，请在具体 Step 中提供默认值
        set_debug_var('status', 'running')
        result = step.run()
        set_debug_var('status', 'cleanup')
        step999.run()
        set_debug_var('status', 'done')
        set_debug_var('result', result)
        return result
    except Exception as e:
        set_debug_var('status', f'error: {e}')
        return False

def start_step_thread(step_name: str) -> threading.Thread:
    """为 UI 提供的异步执行入口，返回线程对象。"""
    def _worker():
        run_step(step_name)
    th = threading.Thread(target=_worker, daemon=True)
    th.start()
    return th
