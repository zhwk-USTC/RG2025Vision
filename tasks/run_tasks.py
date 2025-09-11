from time import sleep

from .steps.step_0_init_selfcheck import Step0InitSelfcheck
from .steps.step_1_1_nav_center import Step11NavCenter
from .steps.step_1_2_search_tag import Step12SearchTag
from .steps.step_2_1_detect_leftmost import Step21DetectLeftmostDart
from .steps.step_2_2_align_base import Step22AlignBase
from .steps.step_2_3_align_arm import Step23AlignArm
from .steps.step_3_1_to_firespot import Step31ToFirespot
from .steps.step_3_2_target_prep import Step32TargetPrep
from .steps.step_3_3_fire import Step33Fire
from .steps.step_999_cleanup import Step999Cleanup

def run_step(target: str):
    """
    运行指定名称的任务步骤
    :param target: 步骤类名字符串，如 'Step11NavCenter'
    """
    step_classes = {
        # "Step0InitSelfcheck": Step0InitSelfcheck,
        "Step11NavCenter": Step11NavCenter,
        "Step12SearchTag": Step12SearchTag,
        "Step21DetectLeftmostDart": Step21DetectLeftmostDart,
        "Step22AlignBase": Step22AlignBase,
        "Step23AlignArm": Step23AlignArm,
        "Step31ToFirespot": Step31ToFirespot,
        "Step32TargetPrep": Step32TargetPrep,
        "Step33Fire": Step33Fire,
        # "Step999Cleanup": Step999Cleanup,
    }
    step_class = step_classes.get(target)
    if step_class is None:
        print(f"未找到指定步骤: {target}")
        return False
    step_instance = step_class()
    if hasattr(step_instance, "run"):
        step0 = Step0InitSelfcheck()
        step999 = Step999Cleanup()
        step0.run()
        result = step_instance.run()
        step999.run()
        print(f"{target} 运行结果: {result}")
        return result
    else:
        print(f"{target} 没有 run 方法")
        return False
