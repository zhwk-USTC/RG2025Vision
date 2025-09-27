from communicate import Var, send_kv, get_latest_decoded, VAR_META
from communicate.protocol.protocol_py.data import _as_float32_le, _unpack_fixed_le_int
import time
from time import sleep
from typing import Literal, Optional
from communicate.protocol.protocol_py.data import DataPacket

def wait_for_ack(var: Var, expected_value: int, timeout: float = -1) -> bool:
    """
    等待指定变量的ACK确认
    
    Args:
        var: 要等待确认的变量
        expected_value: 期望的变量值
        timeout: 超时时间（秒），-1表示无超时
    
    Returns:
        bool: True表示收到确认，False表示超时
    """
    # 使用wait_for_value获取实际值
    actual_value = wait_for_value(var, timeout if timeout > 0 else 10.0)  # 默认10秒超时
    
    # 检查是否匹配期望值
    if actual_value is not None and actual_value == expected_value:
        return True
    return False


def wait_for_value(var: Var, timeout: float = 5.0):
    """
    等待指定变量的值并返回
    使用communicate模块的解析函数和变量元数据
    
    Args:
        var: 要等待的变量
        timeout: 超时时间（秒）
    
    Returns:
        解析后的值，如果超时则返回None
    """
    start_time = time.time()
    
    while True:
        packet = get_latest_decoded()
        if packet is not None and isinstance(packet, DataPacket):
            for tlv in packet.tlvs:
                if tlv.t == var:
                    # 使用VAR_META获取变量类型信息
                    var_meta = VAR_META.get(int(var))
                    if var_meta is None:
                        # 如果没有元数据，回退到基本解析
                        return None
                    
                    vtype = var_meta.get("vtype")
                    if vtype is None:
                        return _unpack_fixed_le_int(tlv.v)
                    
                    # 根据变量类型使用对应的解析函数
                    if vtype == "F32":
                        return _as_float32_le(tlv.v)
                    elif vtype in ["BOOL", "U8", "U16", "U32"]:
                        return _unpack_fixed_le_int(tlv.v)
                    else:
                        # 未知类型，使用基本解析
                        return None
        
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            return None
        sleep(0.1)

# --- 底盘相关 ---

def base_set_move(dir: Literal['forward_fast', 'forward_slow', 'backward_fast', 'backward_slow', 'left_fast', 'left_slow', 'right_fast', 'right_slow', 'forward_fast_ex', 'backward_fast_ex']):
    match dir:
        case 'forward_fast':
            send_kv({Var.BASE_MOVE_FORWARD_FAST: True})
        case 'forward_slow':
            send_kv({Var.BASE_MOVE_FORWARD_SLOW: True})
        case 'backward_fast':
            send_kv({Var.BASE_MOVE_BACKWARD_FAST: True})
        case 'backward_slow':
            send_kv({Var.BASE_MOVE_BACKWARD_SLOW: True})
        case 'left_fast':
            send_kv({Var.BASE_MOVE_LEFT_FAST: True})
        case 'left_slow':
            send_kv({Var.BASE_MOVE_LEFT_SLOW: True})
        case 'right_fast':
            send_kv({Var.BASE_MOVE_RIGHT_FAST: True})
        case 'right_slow':
            send_kv({Var.BASE_MOVE_RIGHT_SLOW: True})
        case 'forward_fast_ex':
            send_kv({Var.BASE_MOVE_FORWARD_FAST_EX: True})
        case 'backward_fast_ex':
            send_kv({Var.BASE_MOVE_BACKWARD_FAST_EX: True})
            
def base_set_rotate(dir: Literal['cw_fast', 'cw_slow', 'ccw_fast', 'ccw_slow']):
    match dir:
        case 'cw_fast':
            send_kv({Var.BASE_ROTATE_CW_FAST: True})
        case 'cw_slow':
            send_kv({Var.BASE_ROTATE_CW_SLOW: True})
        case 'ccw_fast':
            send_kv({Var.BASE_ROTATE_CCW_FAST: True})
        case 'ccw_slow':
            send_kv({Var.BASE_ROTATE_CCW_SLOW: True})
            
def base_stop():
    send_kv({Var.BASE_STOP: True})
    
def imu_reset():
    send_kv({Var.IMU_RESET: True})
    wait_for_ack(Var.OK, int(Var.IMU_RESET), 10)
    
def imu_get_yaw() -> Optional[float]:
    """获取IMU的yaw角度值"""
    send_kv({Var.GET_IMU_YAW: True})
    return wait_for_value(Var.IMU_YAW, timeout=5.0)



# --- 机械臂相关 ---
def arm_reset():
    """上电进入复位"""
    send_kv({Var.ARM_RESET: True})
    wait_for_ack(Var.OK, int(Var.ARM_RESET), 10)
    
def arm_reset_to_store():
    """复位 -> 存储"""
    send_kv({Var.ARM_RESET_TO_STORE: True})
    wait_for_ack(Var.OK, int(Var.ARM_RESET_TO_STORE), 10)

def arm_low_prepare_to_grip():
    """低位准备 -> 夹取"""
    send_kv({Var.ARM_LOW_PREPARE_TO_GRIP: True})
    wait_for_ack(Var.OK, int(Var.ARM_LOW_PREPARE_TO_GRIP), 10)

def arm_reset_to_high_prepare():
    """复位 -> 高位准备"""
    send_kv({Var.ARM_RESET_TO_HIGH_PREPARE: True})
    wait_for_ack(Var.OK, int(Var.ARM_RESET_TO_HIGH_PREPARE), 10)
    
def arm_reset_to_low_prepare():
    """复位 -> 低位准备"""
    send_kv({Var.ARM_RESET_TO_LOW_PREPARE: True})
    wait_for_ack(Var.OK, int(Var.ARM_RESET_TO_LOW_PREPARE), 10)

def arm_high_prepare_to_grip():
    """高位准备 -> 夹取"""
    send_kv({Var.ARM_HIGH_PREPARE_TO_GRIP: True})
    wait_for_ack(Var.OK, int(Var.ARM_HIGH_PREPARE_TO_GRIP), 10)

def arm_store_to_reset():
    """存储 -> 复位（返回初始状态）"""
    send_kv({Var.ARM_STORE_TO_RESET: True})
    wait_for_ack(Var.OK, int(Var.ARM_STORE_TO_RESET), 10)

def arm_shot_to_reset():
    """射击 -> 复位（返回初始状态）"""
    send_kv({Var.ARM_SHOT_TO_RESET: True})
    wait_for_ack(Var.OK, int(Var.ARM_SHOT_TO_RESET), 10)

def arm_high_grip_to_shot():
    """高位夹取 -> 射击"""
    send_kv({Var.ARM_HIGH_GRIP_TO_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_HIGH_GRIP_TO_SHOT), 10)

def arm_store_to_shot():
    """存储 -> 射击"""
    send_kv({Var.ARM_STORE_TO_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_STORE_TO_SHOT), 10)

def arm_low_grip_to_wait_shot():
    """低位夹取 -> 等待射击"""
    send_kv({Var.ARM_LOW_GRIP_TO_WAIT_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_LOW_GRIP_TO_WAIT_SHOT), 10)

def arm_high_grip_to_wait_shot():
    """高位夹取 -> 等待射击"""
    send_kv({Var.ARM_HIGH_GRIP_TO_WAIT_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_HIGH_GRIP_TO_WAIT_SHOT), 10)

def arm_wait_shot_to_shot():
    """等待射击 -> 射击"""
    send_kv({Var.ARM_WAIT_SHOT_TO_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_WAIT_SHOT_TO_SHOT), 10)

def arm_high_grip_to_store():
    """高位夹取 -> 存储"""
    send_kv({Var.ARM_HIGH_GRIP_TO_STORE: True})
    wait_for_ack(Var.OK, int(Var.ARM_HIGH_GRIP_TO_STORE), 10)

def arm_low_grip_to_store():
    """低位夹取 -> 存储"""
    send_kv({Var.ARM_LOW_GRIP_TO_STORE: True})
    wait_for_ack(Var.OK, int(Var.ARM_LOW_GRIP_TO_STORE), 10)

def arm_low_grip_to_shot():
    """低位夹取 -> 射击"""
    send_kv({Var.ARM_LOW_GRIP_TO_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_LOW_GRIP_TO_SHOT), 10)
    
def set_fire_speed(speed: float):
    send_kv({Var.FRICTION_WHEEL_SPEED: speed})
    
def fire_once():
    send_kv({Var.FIRE_ONCE:True})
    wait_for_ack(Var.OK, int(Var.FIRE_ONCE), 30)

def dart_push_once():
    """推进飞镖向前，然后回到原位"""
    send_kv({Var.DART_PUSH_ONCE: True})
    wait_for_ack(Var.OK, int(Var.DART_PUSH_ONCE), 10)

def set_friction_wheel_speed(speed: float):
    """设置摩擦轮速度"""
    send_kv({Var.FRICTION_WHEEL_SPEED: speed})

def friction_wheel_start():
    """启动摩擦轮"""
    send_kv({Var.FRICTION_WHEEL_START: True})
    wait_for_ack(Var.OK, int(Var.FRICTION_WHEEL_START), 10)

def friction_wheel_stop():
    """停止摩擦轮"""
    send_kv({Var.FRICTION_WHEEL_STOP: True})
    wait_for_ack(Var.OK, int(Var.FRICTION_WHEEL_STOP), 10)

# --- 炮台相关 ---
def turret_set_yaw(angle: float):
    # 确保角度在有效范围内
    angle = max(-1.0, min(1.0, angle))
    send_kv({Var.TURRET_ANGLE_YAW: angle})
    time.sleep(1.0)  # 等待炮台转动到位

def get_voltage() -> Optional[float]:
    """获取当前电压值"""
    send_kv({Var.GET_VOLTAGE: True})
    return wait_for_value(Var.VOLTAGE, timeout=5.0)


