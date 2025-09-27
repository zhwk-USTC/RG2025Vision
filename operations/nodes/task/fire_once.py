from typing import Optional
from ...utils.communicate_utils import set_fire_speed, fire_once, get_voltage
from ...debug_vars_enhanced import set_debug_var, DebugLevel, DebugCategory
from core.logger import logger

class FireOnce:
    """
    通用发射控制任务
    支持设置发射脉冲长度和发射，支持电压校正
    """

    def __init__(self, fire_speed: Optional[float] = None, calibrate_voltage: bool = False):
        """
        参数：
        - fire_speed: 发射脉冲长度（1000-2000，如果为None则不设置）
        - calibrate_voltage: 是否根据当前电压校正发射脉冲长度（标称电压24.0V）
        """
        self.fire_speed = fire_speed
        self.calibrate_voltage = calibrate_voltage

    def run(self) -> bool:
        logger.info(f"[FireControl] 开始发射控制，发射1次")
        
        try:
            # 设置发射速度（如果指定）
            speed_to_set = None
            if self.fire_speed is not None:
                speed_to_set = self.fire_speed
                if self.calibrate_voltage:
                    current_voltage = get_voltage()
                    if current_voltage is not None and current_voltage > 0:
                        # 电压校正：pulse_width_new = 1000 + (pulse_width_original - 1000) * (24.0 / current_voltage)
                        speed_to_set = 1000 + (self.fire_speed - 1000) * (24.0 / current_voltage)
                        # 确保脉冲长度在有效范围内 (1000-2000)
                        speed_to_set = max(1000.0, min(2000.0, speed_to_set))
                        logger.info(f"[FireControl] 电压校正：当前电压 {current_voltage}V，标称电压 24.0V，校正后脉冲长度 {speed_to_set}")
                        set_debug_var('voltage_calibration', f"{current_voltage}V -> {speed_to_set}", 
                                     DebugLevel.INFO, DebugCategory.CONTROL, "电压校正已应用")
                    else:
                        logger.warning("[FireControl] 无法获取当前电压，跳过校正")
                        set_debug_var('voltage_calibration_error', '无法获取电压', 
                                     DebugLevel.WARNING, DebugCategory.ERROR, "电压校正失败")
                
                set_fire_speed(float(speed_to_set))
                set_debug_var('fire_speed_set', speed_to_set, 
                             DebugLevel.INFO, DebugCategory.CONTROL, "发射脉冲长度已设置")
                logger.info(f"[FireControl] 发射脉冲长度设置为: {speed_to_set}")
            
            # 执行发射
            fire_once()
            logger.info(f"[FireControl] 第1次发射完成")
            set_debug_var(f'fire_1_done', True, 
                         DebugLevel.SUCCESS, DebugCategory.STATUS, f"第1次发射完成")

            # 记录发射后的脉冲长度和电压
            final_voltage = get_voltage()
            logger.info(f"[FireControl] 发射完成 - 脉冲长度: {speed_to_set if speed_to_set is not None else '未设置'}, 电压: {final_voltage}V")
            set_debug_var('fire_final_status', f"脉冲长度:{speed_to_set if speed_to_set is not None else '未设置'}, 电压:{final_voltage}V", 
                         DebugLevel.INFO, DebugCategory.STATUS, "发射完成状态")

            set_debug_var('fire_control_status', 'success', 
                         DebugLevel.SUCCESS, DebugCategory.STATUS, "发射控制成功完成")
            logger.info("[FireControl] 发射控制完成")
            
        except Exception as e:
            logger.error(f"[FireControl] 发射控制异常：{e}")
            set_debug_var('fire_control_error', str(e), 
                         DebugLevel.ERROR, DebugCategory.ERROR, "发射控制时发生错误")
            return False
        
        return True