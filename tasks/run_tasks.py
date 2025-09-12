import threading
import time
from .steps.step_00_init import Step00Init
from .steps.step_11_nav_center import Step11NavCenter
from .steps.step_12_align_stand import Step12AlignStand
from .steps.step_21_align_base import Step21AlignBase
from .steps.step_22_align_arm import Step22AlignArm
from .steps.step_23_grasp import Step23Grasp
from .steps.step_24_load import Step24Load
from .steps.step_31_move_fire import Step31MoveFire
from .steps.step_32_fire import Step32Fire
from .steps.step_99_cleanup import Step999Cleanup
from .debug_vars_enhanced import reset_debug_vars, set_debug_var, DebugLevel, DebugCategory

# 全局任务线程管理
_current_thread = None
_stop_requested = False

_STEP_CLASSES = {
    "Step11NavCenter": Step11NavCenter,
    "Step12AlignStand": Step12AlignStand,
    "Step21AlignBase": Step21AlignBase,
    "Step22AlignArm": Step22AlignArm,
    "Step23Grasp": Step23Grasp,
    "Step24Load": Step24Load,
    "Step31MoveFire": Step31MoveFire,
    "Step32Fire": Step32Fire,
}

def force_stop_current_task():
    """强制停止当前正在运行的任务"""
    global _current_thread, _stop_requested
    
    _stop_requested = True
    set_debug_var('task_stop_requested', True, DebugLevel.WARNING, DebugCategory.STATUS, "用户请求强制停止任务")
    
    # 标记线程应该停止（线程需要自己检查此标志）
    if _current_thread and _current_thread.is_alive():
        # 给任务3秒时间停止
        _current_thread.join(timeout=3.0)
        if _current_thread.is_alive():
            set_debug_var('task_still_running', True, DebugLevel.WARNING, DebugCategory.STATUS, "任务仍在运行，可能卡死")
        else:
            set_debug_var('task_stopped', True, DebugLevel.SUCCESS, DebugCategory.STATUS, "任务已停止")
    
    _current_thread = None
    _stop_requested = False

def is_task_running():
    """检查是否有任务正在运行"""
    global _current_thread
    return _current_thread is not None and _current_thread.is_alive()

def run_step(step_name: str):
    """同步执行（阻塞）一个步骤，主要用于脚本调用。"""
    step_cls = _STEP_CLASSES.get(step_name)
    if not step_cls:
        return False
    reset_debug_vars()
    set_debug_var('current_step', step_name, DebugLevel.INFO, DebugCategory.STATUS, f"当前运行步骤: {step_name}")
    set_debug_var('status', 'init', DebugLevel.INFO, DebugCategory.STATUS, "任务初始化中")
    step0 = Step00Init()
    step999 = Step999Cleanup()
    try:
        set_debug_var('status', 'selfcheck', DebugLevel.INFO, DebugCategory.STATUS, "执行自检")
        step0.run()
        
        step = step_cls()  # 若需要参数，请在具体 Step 中提供默认值
        set_debug_var('status', 'running', DebugLevel.INFO, DebugCategory.STATUS, "执行主要步骤")
        result = step.run()
            
        set_debug_var('status', 'cleanup', DebugLevel.INFO, DebugCategory.STATUS, "执行清理")
        step999.run()
        set_debug_var('status', 'done', DebugLevel.SUCCESS, DebugCategory.STATUS, "任务完成")
        set_debug_var('result', result, DebugLevel.SUCCESS, DebugCategory.STATUS, f"任务结果: {result}")
        return result
    except Exception as e:
        set_debug_var('status', f'error: {e}', DebugLevel.ERROR, DebugCategory.ERROR, f"任务执行异常: {e}")
        return False

def start_step_thread(step_name: str) -> threading.Thread:
    """为 UI 提供的异步执行入口，返回线程对象。"""
    global _current_thread
    
    # 如果已有任务在运行，先停止它
    if is_task_running():
        force_stop_current_task()
        time.sleep(0.1)  # 等待停止完成
    
    def _worker():
        try:
            run_step(step_name)
        finally:
            # 任务完成后清理
            global _current_thread
            _current_thread = None
    
    _current_thread = threading.Thread(target=_worker, daemon=True)
    _current_thread.start()
    return _current_thread
