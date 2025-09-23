from typing import Optional
from ....utils.communicate_utils import imu_get_yaw, base_set_rotate, base_stop
from ....utils.base_movement_utils import MovementUtils
import time
import math

class BaseRotateByAngle:
    """
    底盘旋转指定角度的任务节点
    使用IMU反馈的闭环控制，根据角度误差自动选择旋转速度
    角度误差大时使用快速旋转，角度误差小时使用慢速旋转
    """

    DEFAULT_TOLERANCE_DEGREES = 3.0

    def __init__(self,
                 angle_degrees: float,
                 tolerance_degrees: float = DEFAULT_TOLERANCE_DEGREES):
        """
        构造底盘旋转指定角度任务节点

        Args:
            angle_degrees: 要旋转的角度（度），正值顺时针，负值逆时针
            tolerance_degrees: 角度误差容忍度（度），默认 DEFAULT_TOLERANCE_DEGREES
            max_pulse_duration: 最大脉冲持续时间（秒），默认 DEFAULT_MAX_PULSE_DURATION
            min_pulse_duration: 最小脉冲持续时间（秒），默认 DEFAULT_MIN_PULSE_DURATION
            fast_threshold_degrees: 使用快速旋转的角度误差阈值（度），默认 DEFAULT_FAST_THRESHOLD_DEGREES
        """
        self.angle_degrees = angle_degrees
        self.tolerance_degrees = tolerance_degrees

    def run(self) -> bool:
        """
        执行底盘旋转（闭环控制）
        根据角度误差自动选择旋转速度：
        - 角度误差 > fast_threshold_degrees：使用快速旋转
        - 角度误差 ≤ fast_threshold_degrees：使用慢速旋转

        Returns:
            bool: 旋转成功返回True，失败返回False
        """
        try:
            # 获取当前角度作为起始角度
            start_angle = imu_get_yaw()
            if start_angle is None:
                print(f"[BaseRotateByAngle] 无法获取当前IMU角度")
                return False

            # 将起始角度归一化到-180到180度范围
            start_angle = ((start_angle + 180) % 360) - 180

            # 计算目标角度
            target_angle = start_angle + self.angle_degrees

            # 将角度归一化到-180到180度范围
            target_angle = ((target_angle + 180) % 360) - 180

            print(f"[BaseRotateByAngle] 当前角度: {start_angle:.1f}°, 目标角度: {target_angle:.1f}°, 旋转角度: {self.angle_degrees:.1f}°")

            while True:
                # 获取当前角度
                current_angle = imu_get_yaw()
                if current_angle is None:
                    break

                # 将当前角度归一化到-180到180度范围
                current_angle = ((current_angle + 180) % 360) - 180

                # 计算角度误差（考虑角度循环）
                angle_diff = target_angle - current_angle
                # 归一化到-180到180度范围
                while angle_diff > 180:
                    angle_diff -= 360
                while angle_diff < -180:
                    angle_diff += 360

                angle_error_abs = abs(angle_diff)

                print(f"[BaseRotateByAngle] 当前角度: {current_angle:.1f}°, 目标角度: {target_angle:.1f}°, 误差: {angle_error_abs:.1f}°")

                # 检查是否到达目标角度
                if angle_error_abs <= self.tolerance_degrees:
                    base_stop()
                    print(f"[BaseRotateByAngle] 旋转完成，当前角度: {current_angle:.1f}°, 误差: {angle_error_abs:.1f}°")
                    return True
                
                MovementUtils.execute_rotate_by_angle(math.radians(angle_diff))
            print(f"[BaseRotateByAngle] 旋转失败，无法获取IMU角度")
            return False

        except Exception as e:
            base_stop()  # 确保停止旋转
            print(f"[BaseRotateByAngle] 旋转异常: {e}")
            return False