"""
基础移动工具函数模块
包含平滑过渡移动控制等通用移动功能
"""

import time
from typing import Optional, Literal
from .communicate_utils import base_set_move, base_set_rotate, base_stop

# ---------------------------
# 平滑移动参数（可按实际调参）
# ---------------------------

# 平移脉冲最小/最大时长（秒）
MOVE_PULSE_MIN_SEC = 0.05
MOVE_PULSE_MAX_SEC = 2.00
# 旋转脉冲最小/最大时长（秒）
ROT_PULSE_MIN_SEC = 0.05
ROT_PULSE_MAX_SEC = 2.00

# 速度参数（米/秒）
MOVE_SPEED_SLOW_MPS = 0.1    # 慢速移动速度
MOVE_SPEED_FAST_MPS = 0.3    # 快速移动速度
MOVE_FAST_THR_M = 0.30      # 平移快慢阈值（m）

# 旋转速度参数（弧度/秒）
ROT_SPEED_SLOW_RPS = 22 * 3.141592653589793 / 180    # 慢速旋转角速度 (22度/秒)
ROT_SPEED_FAST_RPS = 45 * 3.141592653589793 / 180    # 快速旋转角速度 (45度/秒)
ROT_FAST_THR_RAD = 0.50     # 旋转快慢阈值（rad）

# 运动指令执行等待时长（秒）
MOVE_WAIT_BASE_SEC = 0.5

# 移动命令类型
MoveCommand = Literal['forward_fast', 'forward_slow', 'backward_fast', 'backward_slow',
                      'left_fast', 'left_slow', 'right_fast', 'right_slow']
MoveDirection = Literal['forward', 'backward', 'left', 'right']

# 旋转命令类型
RotateCommand = Literal['cw_fast', 'cw_slow', 'ccw_fast', 'ccw_slow']
RotateDirection = Literal['cw', 'ccw']


class MovementUtils:
    """基础移动控制工具函数"""

    @staticmethod
    def execute_move(move_cmd: MoveCommand, pulse_sec: float) -> None:
        """
        执行移动命令

        参数:
            move_cmd: 移动命令
            pulse_sec: 移动脉冲时长（秒）
        """
        pulse_sec = max(MOVE_PULSE_MIN_SEC, min(MOVE_PULSE_MAX_SEC, pulse_sec))
        if not move_cmd or pulse_sec <= 0:
            base_stop()
            return

        base_set_move(move_cmd)
        time.sleep(pulse_sec)
        base_stop()
        time.sleep(MOVE_WAIT_BASE_SEC)

    @staticmethod
    def execute_rotate(rot_cmd: RotateCommand, pulse_sec: float) -> None:
        """
        执行旋转命令

        参数:
            rot_cmd: 旋转命令
            pulse_sec: 旋转脉冲时长（秒）
        """
        pulse_sec = max(ROT_PULSE_MIN_SEC, min(ROT_PULSE_MAX_SEC, pulse_sec))
        if not rot_cmd or pulse_sec <= 0:
            base_stop()
            return

        base_set_rotate(rot_cmd)
        time.sleep(pulse_sec)

        # 停止并等待稳定
        base_stop()
        time.sleep(MOVE_WAIT_BASE_SEC)

    @staticmethod
    def stop_movement() -> None:
        """停止所有移动"""
        base_stop()
        time.sleep(MOVE_WAIT_BASE_SEC)

    @staticmethod
    def execute_move_by_distance(move_dir: MoveDirection, distance_m: float) -> None:
        """
        执行指定方向和距离的移动命令

        参数:
            move_dir: 移动方向
            distance_m: 移动距离（米）
        """
        if not move_dir or distance_m <= 0:
            base_stop()
            return

        if distance_m < MOVE_FAST_THR_M:
            speed_suffix = '_slow'
            speed = MOVE_SPEED_SLOW_MPS
        else:
            speed_suffix = '_fast'
            speed = MOVE_SPEED_FAST_MPS

        # 根据速度选择移动脉冲时长
        pulse_sec = distance_m * 0.8 / speed

        # 根据方向选择移动命令
        move_cmd = f"{move_dir}{speed_suffix}"

        MovementUtils.execute_move(move_cmd, pulse_sec)  # type: ignore

    @staticmethod
    def execute_rotate_by_angle(angle_rad: float) -> None:
        """
        执行指定方向和角度的旋转命令

        参数:
            angle_rad: 旋转角度（弧度）
        """
        if angle_rad <= 0:
            rot_dir = 'cw'
        else:
            rot_dir = 'ccw'

        abs_angle_rad = abs(angle_rad)

        if abs_angle_rad < ROT_FAST_THR_RAD:
            speed_suffix = '_slow'
            speed = ROT_SPEED_SLOW_RPS
        else:
            speed_suffix = '_fast'
            speed = ROT_SPEED_FAST_RPS

        # 根据速度选择旋转脉冲时长
        pulse_sec = abs_angle_rad * 0.8 / speed

        # 根据方向选择旋转命令
        rot_cmd = f"{rot_dir}{speed_suffix}"

        MovementUtils.execute_rotate(rot_cmd, pulse_sec)  # type: ignore
