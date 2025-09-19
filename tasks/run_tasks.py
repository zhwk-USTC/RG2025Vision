# tasks/run_tasks.py
import threading
import time
from typing import List, Optional

from .steps.step_00_init import Step00Init
from .steps.step_11_nav_center import Step11NavCenter
from .steps.step_12_align_stand import Step12AlignStand
from .steps.step_21_align_base import Step21AlignBase
from .steps.step_22_align_arm import Step22AlignArm
from .steps.step_23_grasp_load import Step23GraspLoad
from .steps.step_31_move_fire import Step31MoveFire
from .steps.step_32_fire import Step32Fire
from .steps.step_99_cleanup import Step999Cleanup
from .debug_vars_enhanced import reset_debug_vars, set_debug_var, DebugLevel, DebugCategory

# 线程状态
_current_thread = None
_stop_requested = False

# 步骤名到类的映射（保留）
_STEP_CLASSES = {
    "Step11NavCenter": Step11NavCenter,
    "Step12AlignStand": Step12AlignStand,
    "Step21AlignBase": Step21AlignBase,
    "Step22AlignArm": Step22AlignArm,
    "Step23GraspLoad": Step23GraspLoad,
    "Step31MoveFire": Step31MoveFire,
    "Step32Fire": Step32Fire,
}

# ===== 新增：从 config 读取顺序 =====
def _load_task_sequence() -> List[dict]:
    """加载任务配置，返回包含步骤名称和参数的完整配置信息"""
    try:
        from core.config.tasks_config import load_tasks_config
        config = load_tasks_config()
        # 过滤未知步骤名，避免因拼写错误导致崩溃，同时保留参数
        tasks = []
        for task in config.tasks:
            if task.name in _STEP_CLASSES:
                tasks.append({
                    'name': task.name, 
                    'parameters': task.parameters if task.parameters else {}
                })
        return tasks
    except Exception:
        # 回退到默认顺序（等价于你原来的"组"按自然顺序拼接）
        return [{'name': name, 'parameters': {}} for name in _STEP_CLASSES.keys()]

def is_stop_requested():
    return _stop_requested

def check_stop_request():
    if is_stop_requested():
        raise TaskStoppedException("Task stopped by user request")

class TaskStoppedException(Exception):
    pass

def force_stop_current_task():
    """强制停止当前任务，并执行清理"""
    global _current_thread, _stop_requested

    _stop_requested = True
    set_debug_var('task_stop_requested', True, DebugLevel.WARNING, DebugCategory.STATUS, "用户请求强制停止任务")

    if _current_thread and _current_thread.is_alive():
        set_debug_var('stop_phase', 'cooperative_stop', DebugLevel.INFO, DebugCategory.STATUS, "等待任务协作停止")
        _current_thread.join(timeout=5.0)

        if _current_thread.is_alive():
            set_debug_var('stop_phase', 'force_interrupt', DebugLevel.WARNING, DebugCategory.STATUS, "协作停止失败，尝试强制中断")
            _current_thread.join(timeout=2.0)
            if _current_thread.is_alive():
                set_debug_var('task_still_running', True, DebugLevel.ERROR, DebugCategory.STATUS, "任务仍在运行，线程可能卡死")
                set_debug_var('stop_recommendation', 'restart_required', DebugLevel.ERROR, DebugCategory.STATUS, "建议重启程序以完全清理卡死的任务")
            else:
                set_debug_var('task_stopped', True, DebugLevel.SUCCESS, DebugCategory.STATUS, "任务已强制停止")
        else:
            set_debug_var('task_stopped', True, DebugLevel.SUCCESS, DebugCategory.STATUS, "任务已协作停止")
    else:
        set_debug_var('no_task_running', True, DebugLevel.INFO, DebugCategory.STATUS, "没有正在运行的任务")

    # 无论线程状态如何，都执行清理
    try:
        set_debug_var('cleanup_phase', 'starting', DebugLevel.INFO, DebugCategory.STATUS, "开始强制清理")
        Step999Cleanup(open_gripper_on_exit=False).run()
        set_debug_var('cleanup_phase', 'completed', DebugLevel.SUCCESS, DebugCategory.STATUS, "强制清理已完成")
    except Exception as e:
        set_debug_var('cleanup_error', f'Cleanup exception: {e}', DebugLevel.ERROR, DebugCategory.ERROR, f"强制清理异常: {e}")

    _current_thread = None
    _stop_requested = False
    set_debug_var('force_stop_completed', True, DebugLevel.SUCCESS, DebugCategory.STATUS, "强制停止流程已完成")

def is_task_running():
    global _current_thread
    return _current_thread is not None and _current_thread.is_alive()

def run_step(step_name: str, **kwargs):
    """同步执行单步：Step00Init -> step -> Step999Cleanup。支持构造参数 kwargs。"""
    step_cls = _STEP_CLASSES.get(step_name)
    if not step_cls:
        set_debug_var('error', f'Unknown step: {step_name}', DebugLevel.ERROR, DebugCategory.ERROR, f"未知步骤: {step_name}")
        return False

    reset_debug_vars()
    set_debug_var('current_step', step_name, DebugLevel.INFO, DebugCategory.STATUS, f"当前运行步骤: {step_name}")
    set_debug_var('status', 'init', DebugLevel.INFO, DebugCategory.STATUS, "任务初始化中")

    step0 = Step00Init()
    step999 = Step999Cleanup()

    try:
        if is_stop_requested():
            raise TaskStoppedException("Task stopped during initialization")

        set_debug_var('status', 'selfcheck', DebugLevel.INFO, DebugCategory.STATUS, "执行自检")
        step0.run()

        if is_stop_requested():
            raise TaskStoppedException("Task stopped before main step")

        if kwargs:
            set_debug_var('step_params', kwargs, DebugLevel.INFO, DebugCategory.STATUS, f"步骤参数: {kwargs}")

        set_debug_var('status', 'running', DebugLevel.INFO, DebugCategory.STATUS, "执行主要步骤")
        result = step_cls(**kwargs).run()

        if is_stop_requested():
            set_debug_var('status', 'stopped_after_completion', DebugLevel.WARNING, DebugCategory.STATUS, "任务完成后被停止")
        else:
            set_debug_var('status', 'completed', DebugLevel.SUCCESS, DebugCategory.STATUS, "主要步骤完成")

        set_debug_var('status', 'cleanup', DebugLevel.INFO, DebugCategory.STATUS, "执行清理")
        step999.run()

        if not is_stop_requested():
            set_debug_var('status', 'done', DebugLevel.SUCCESS, DebugCategory.STATUS, "任务完成")
            set_debug_var('result', result, DebugLevel.SUCCESS, DebugCategory.STATUS, f"任务结果: {result}")

        return result

    except TaskStoppedException as e:
        set_debug_var('status', f'stopped: {e}', DebugLevel.WARNING, DebugCategory.STATUS, f"任务被用户停止: {e}")
        try:
            set_debug_var('status', 'forced_cleanup', DebugLevel.INFO, DebugCategory.STATUS, "执行强制清理")
            step999.run()
        except Exception as cleanup_error:
            set_debug_var('cleanup_error', str(cleanup_error), DebugLevel.ERROR, DebugCategory.ERROR, f"强制清理异常: {cleanup_error}")
        return False

    except Exception as e:
        set_debug_var('status', f'error: {e}', DebugLevel.ERROR, DebugCategory.ERROR, f"任务执行异常: {e}")
        try:
            set_debug_var('status', 'error_cleanup', DebugLevel.INFO, DebugCategory.STATUS, "执行异常清理")
            step999.run()
        except Exception as cleanup_error:
            set_debug_var('cleanup_error', str(cleanup_error), DebugLevel.ERROR, DebugCategory.ERROR, f"异常清理失败: {cleanup_error}")
        return False

def run_full_process() -> bool:
    """
    执行全流程（修改版）：
      Step00Init -> 依序执行任务配置中的步骤（含参数） -> Step999Cleanup
    """
    global _stop_requested

    # 获取包含参数的任务序列
    task_configs = _load_task_sequence()

    reset_debug_vars()
    set_debug_var('full_process_status', 'starting', DebugLevel.INFO, DebugCategory.STATUS, "全流程开始")
    set_debug_var('process_sequence', [t['name'] for t in task_configs], DebugLevel.INFO, DebugCategory.STATUS, f"执行顺序: {[t['name'] for t in task_configs]}")

    # 校验步骤存在
    for task_config in task_configs:
        if task_config['name'] not in _STEP_CLASSES:
            set_debug_var('error', f'Unknown step: {task_config["name"]}', DebugLevel.ERROR, DebugCategory.ERROR, f"未知步骤: {task_config['name']}")
            return False

    success = False
    step0 = Step00Init()
    step99 = Step999Cleanup()

    try:
        # 初始化
        if is_stop_requested():
            raise TaskStoppedException("Task stopped before initialization")
        set_debug_var('current_phase', 'initialization', DebugLevel.INFO, DebugCategory.STATUS, "当前阶段：初始化")
        if not step0.run():
            set_debug_var('error', 'Step0 initialization failed', DebugLevel.ERROR, DebugCategory.ERROR, "初始化步骤失败")
            return False
        if is_stop_requested():
            raise TaskStoppedException("Task stopped after initialization")

        # 顺序执行，使用配置参数
        for i, task_config in enumerate(task_configs, start=1):
            step_name = task_config['name']
            parameters = task_config['parameters']
            
            if is_stop_requested():
                raise TaskStoppedException(f"Task stopped before step {step_name}")

            set_debug_var('current_phase', f'seq_{i}_{step_name}', DebugLevel.INFO, DebugCategory.STATUS, f"顺序第{i}步：{step_name}")
            
            # 显示参数信息
            if parameters:
                set_debug_var('step_params', parameters, DebugLevel.INFO, DebugCategory.STATUS, f"步骤参数: {parameters}")

            step_cls = _STEP_CLASSES[step_name]
            # 使用配置中的参数实例化步骤
            result = step_cls(**parameters).run()

            if is_stop_requested():
                raise TaskStoppedException(f"Task stopped after {step_name}")

            if not result:
                reason = f'{step_name} returned false at index {i}'
                set_debug_var('sequence_stop_reason', reason, DebugLevel.ERROR, DebugCategory.ERROR, f"顺序执行停止：{step_name} 返回失败")
                return False

        set_debug_var('full_process_status', 'completed_normally', DebugLevel.SUCCESS, DebugCategory.STATUS, f"全流程正常完成：共执行{len(task_configs)}步")
        success = True

    except TaskStoppedException as e:
        set_debug_var('full_process_status', f'stopped: {e}', DebugLevel.WARNING, DebugCategory.STATUS, f"全流程被用户停止: {e}")
        success = False

    except Exception as e:
        set_debug_var('full_process_status', f'error: {e}', DebugLevel.ERROR, DebugCategory.ERROR, f"全流程执行异常: {e}")
        success = False

    finally:
        # 清理
        try:
            set_debug_var('current_phase', 'cleanup', DebugLevel.INFO, DebugCategory.STATUS, "当前阶段：清理")
            ok = step99.run()
            if ok:
                set_debug_var('cleanup_status', 'completed', DebugLevel.SUCCESS, DebugCategory.STATUS, "清理步骤完成")
            else:
                set_debug_var('cleanup_status', 'partial', DebugLevel.WARNING, DebugCategory.STATUS, "清理步骤部分失败")
        except Exception as e:
            set_debug_var('cleanup_error', f'Cleanup exception: {e}', DebugLevel.ERROR, DebugCategory.ERROR, f"清理异常: {e}")

    return success

def run_default_full_process() -> bool:
    return run_full_process()

def start_default_full_process_thread() -> threading.Thread:
    return start_full_process_thread()

def start_step_thread(step_name: str, **kwargs) -> threading.Thread:
    global _current_thread
    if is_task_running():
        force_stop_current_task()
        time.sleep(0.1)

    def _worker():
        try:
            run_step(step_name, **kwargs)
        finally:
            global _current_thread
            _current_thread = None

    _current_thread = threading.Thread(target=_worker, daemon=True)
    _current_thread.start()
    return _current_thread

def start_full_process_thread() -> threading.Thread:
    """异步执行简化全流程；可传入自定义顺序，否则读取 config。"""
    global _current_thread
    if is_task_running():
        force_stop_current_task()
        time.sleep(0.1)

    def _worker():
        try:
            run_full_process()
        finally:
            global _current_thread
            _current_thread = None

    _current_thread = threading.Thread(target=_worker, daemon=True)
    _current_thread.start()
    return _current_thread
