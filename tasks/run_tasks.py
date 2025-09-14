import threading
import time
from typing import List, Optional
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

# 步骤组定义
_STEP_GROUPS = {
    "step1": ["Step11NavCenter", "Step12AlignStand"],
    "step2": ["Step21AlignBase", "Step22AlignArm", "Step23Grasp", "Step24Load"],
    "step3": ["Step31MoveFire", "Step32Fire"]
}

def is_stop_requested():
    """供步骤内部调用，检查是否请求停止"""
    global _stop_requested
    return _stop_requested

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

def run_full_process(step1_group: Optional[List[str]] = None, 
                     step2_group: Optional[List[str]] = None, 
                     step3_group: Optional[List[str]] = None,
                     max_cycles: int = 10) -> bool:
    """
    执行全流程：step0-step1组-step2组-step3组-step2组-...直到返回异常（即run结果是false）-step99
    
    Args:
        step1_group: step1组的步骤列表，默认使用 _STEP_GROUPS["step1"]
        step2_group: step2组的步骤列表（会循环执行），默认使用 _STEP_GROUPS["step2"]
        step3_group: step3组的步骤列表（会循环执行），默认使用 _STEP_GROUPS["step3"]
        max_cycles: 最大循环次数（防止无限循环）
    
    Returns:
        bool: 全流程是否成功完成
    """
    global _stop_requested
    
    # 使用默认步骤组配置
    if step1_group is None:
        step1_group = _STEP_GROUPS["step1"]
    if step2_group is None:
        step2_group = _STEP_GROUPS["step2"]
    if step3_group is None:
        step3_group = _STEP_GROUPS["step3"]
    
    reset_debug_vars()
    set_debug_var('full_process_status', 'starting', DebugLevel.INFO, DebugCategory.STATUS, "全流程开始")
    set_debug_var('process_step1_group', step1_group, DebugLevel.INFO, DebugCategory.STATUS, f"Step1组配置: {step1_group}")
    set_debug_var('process_step2_group', step2_group, DebugLevel.INFO, DebugCategory.STATUS, f"Step2组配置: {step2_group}")
    set_debug_var('process_step3_group', step3_group, DebugLevel.INFO, DebugCategory.STATUS, f"Step3组配置: {step3_group}")
    
    # 检查所有步骤类是否存在
    all_steps = step1_group + step2_group + step3_group
    for step_name in all_steps:
        if step_name not in _STEP_CLASSES:
            set_debug_var('error', f'Unknown step: {step_name}', DebugLevel.ERROR, DebugCategory.ERROR, f"未知步骤: {step_name}")
            return False
    
    # Step 0: 初始化
    try:
        set_debug_var('current_phase', 'initialization', DebugLevel.INFO, DebugCategory.STATUS, "当前阶段：初始化")
        step0 = Step00Init()
        if not step0.run():
            set_debug_var('error', 'Step0 initialization failed', DebugLevel.ERROR, DebugCategory.ERROR, "初始化步骤失败")
            return False
        
        if _stop_requested:
            set_debug_var('status', 'stopped_by_user', DebugLevel.WARNING, DebugCategory.STATUS, "用户请求停止")
            return False
            
    except Exception as e:
        set_debug_var('error', f'Step0 exception: {e}', DebugLevel.ERROR, DebugCategory.ERROR, f"初始化异常: {e}")
        return False
    
    # Step 1 组: 执行所有 step1.x 步骤
    if not _execute_step_group("step1", step1_group, is_loop=False):
        return False
    
    # 循环执行 Step2 组和 Step3 组
    cycle_count = 0
    
    while cycle_count < max_cycles:
        if _stop_requested:
            set_debug_var('status', 'stopped_by_user', DebugLevel.WARNING, DebugCategory.STATUS, "用户请求停止")
            break
            
        cycle_count += 1
        set_debug_var('current_cycle', cycle_count, DebugLevel.INFO, DebugCategory.STATUS, f"当前循环次数: {cycle_count}")
        
        # 执行 Step2 组
        if not _execute_step_group("step2", step2_group, is_loop=True, cycle_count=cycle_count):
            break
            
        # 执行 Step3 组
        if not _execute_step_group("step3", step3_group, is_loop=True, cycle_count=cycle_count):
            break
    
    # Step 99: 清理
    try:
        set_debug_var('current_phase', 'cleanup', DebugLevel.INFO, DebugCategory.STATUS, "当前阶段：清理")
        step99 = Step999Cleanup()
        step99.run()  # 清理步骤的结果不影响整体成功状态
    except Exception as e:
        set_debug_var('cleanup_error', f'Cleanup exception: {e}', DebugLevel.WARNING, DebugCategory.ERROR, f"清理异常: {e}")
    
    # 报告完成状态
    if cycle_count >= max_cycles:
        set_debug_var('full_process_status', 'completed_max_cycles', DebugLevel.SUCCESS, DebugCategory.STATUS, f"全流程完成：达到最大循环次数{max_cycles}")
    else:
        set_debug_var('full_process_status', 'completed_normally', DebugLevel.SUCCESS, DebugCategory.STATUS, f"全流程正常完成：执行了{cycle_count}轮循环")
    
    set_debug_var('total_cycles_executed', cycle_count, DebugLevel.INFO, DebugCategory.STATUS, f"总共执行循环次数: {cycle_count}")
    return True

def _execute_step_group(group_name: str, step_list: List[str], is_loop: bool = False, cycle_count: int = 0) -> bool:
    """
    执行一组步骤
    
    Args:
        group_name: 步骤组名称（用于调试信息）
        step_list: 要执行的步骤列表
        is_loop: 是否为循环执行
        cycle_count: 当前循环次数（仅在循环执行时有效）
    
    Returns:
        bool: 步骤组是否执行成功
    """
    global _stop_requested
    
    for i, step_name in enumerate(step_list):
        if _stop_requested:
            set_debug_var('status', 'stopped_by_user', DebugLevel.WARNING, DebugCategory.STATUS, "用户请求停止")
            return False
            
        try:
            if is_loop:
                phase_name = f'cycle{cycle_count}_{group_name}_{i+1}_{step_name}'
                task_description = f"循环{cycle_count} {group_name}第{i+1}步：{step_name}"
            else:
                phase_name = f'{group_name}_{i+1}_{step_name}'
                task_description = f"{group_name}第{i+1}步：{step_name}"
                
            set_debug_var('current_phase', phase_name, DebugLevel.INFO, DebugCategory.STATUS, task_description)
            
            step_cls = _STEP_CLASSES[step_name]
            step_instance = step_cls()
            result = step_instance.run()
            
            if not result:
                if is_loop:
                    reason = f'{step_name} returned false in cycle {cycle_count} step {i+1}'
                    set_debug_var('cycle_stop_reason', reason, DebugLevel.INFO, DebugCategory.STATUS, f"循环停止：{step_name}在第{cycle_count}轮第{i+1}步返回失败")
                else:
                    reason = f'{step_name} returned false in {group_name} step {i+1}'
                    set_debug_var('group_stop_reason', reason, DebugLevel.ERROR, DebugCategory.ERROR, f"步骤组停止：{step_name}在{group_name}第{i+1}步返回失败")
                return False
                
        except Exception as e:
            if is_loop:
                reason = f'{step_name} exception in cycle {cycle_count} step {i+1}: {e}'
                set_debug_var('cycle_stop_reason', reason, DebugLevel.ERROR, DebugCategory.ERROR, f"循环停止：{step_name}在第{cycle_count}轮第{i+1}步异常: {e}")
            else:
                reason = f'{step_name} exception in {group_name} step {i+1}: {e}'
                set_debug_var('group_stop_reason', reason, DebugLevel.ERROR, DebugCategory.ERROR, f"步骤组停止：{step_name}在{group_name}第{i+1}步异常: {e}")
            return False
    
    # 所有步骤都成功执行
    if is_loop:
        set_debug_var(f'{group_name}_cycle{cycle_count}_completed', True, DebugLevel.SUCCESS, DebugCategory.STATUS, f"循环{cycle_count}的{group_name}组已完成")
    else:
        set_debug_var(f'{group_name}_completed', True, DebugLevel.SUCCESS, DebugCategory.STATUS, f"{group_name}组已完成")
    
    return True

def run_default_full_process() -> bool:
    """运行默认配置的全流程（同步执行，阻塞）"""
    return run_full_process()

def start_default_full_process_thread() -> threading.Thread:
    """启动默认配置的全流程（异步执行）"""
    return start_full_process_thread()

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

def start_full_process_thread(step1_group: Optional[List[str]] = None,
                              step2_group: Optional[List[str]] = None, 
                              step3_group: Optional[List[str]] = None,
                              max_cycles: int = 10) -> threading.Thread:
    """为 UI 提供的全流程异步执行入口，返回线程对象。"""
    global _current_thread
    
    # 如果已有任务在运行，先停止它
    if is_task_running():
        force_stop_current_task()
        time.sleep(0.1)  # 等待停止完成
    
    def _worker():
        try:
            run_full_process(step1_group, step2_group, step3_group, max_cycles)
        finally:
            # 任务完成后清理
            global _current_thread
            _current_thread = None
    
    _current_thread = threading.Thread(target=_worker, daemon=True)
    _current_thread.start()
    return _current_thread
