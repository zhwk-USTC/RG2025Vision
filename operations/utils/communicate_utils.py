from communicate import Var, send_kv, get_latest_decoded
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
    start_time = time.time()
    
    while True:
        # 获取最新接收到的数据包
        packet = get_latest_decoded()
        
        if packet is not None and isinstance(packet, DataPacket):
            # 遍历数据包中的所有TLV项
            for tlv in packet.tlvs:
                if tlv.t == var:
                    # 解析变量值
                    if len(tlv.v) == 1:  # BOOL/U8类型
                        value = int.from_bytes(tlv.v, 'little')
                    elif len(tlv.v) == 2:  # U16类型
                        value = int.from_bytes(tlv.v, 'little')
                    elif len(tlv.v) == 4:  # U32/F32类型
                        value = int.from_bytes(tlv.v, 'little')
                    else:
                        continue
                    
                    if value == expected_value:
                        return True
        
        # 检查超时
        if timeout > 0:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return False
        
        # 短暂休眠避免过度占用CPU
        sleep(0.1)


def base_move(dir: Literal['forward_fast', 'forward_slow', 'backward_fast', 'backward_slow', 'left_fast', 'left_slow', 'right_fast', 'right_slow']):
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
            
def base_stop():
    send_kv({Var.BASE_STOP: True})

def base_rotate(dir: Literal['cw_fast', 'cw_slow', 'ccw_fast', 'ccw_slow']):
    match dir:
        case 'cw_fast':
            send_kv({Var.BASE_ROTATE_CW_FAST: True})
        case 'cw_slow':
            send_kv({Var.BASE_ROTATE_CW_SLOW: True})
        case 'ccw_fast':
            send_kv({Var.BASE_ROTATE_CCW_FAST: True})
        case 'ccw_slow':
            send_kv({Var.BASE_ROTATE_CCW_SLOW: True})

def arm_reset():
    send_kv({Var.ARM_RESET: True})
    wait_for_ack(Var.OK,Var.ARM_RESET, 10)
    
def arm_reset_to_prepare():
    send_kv({Var.ARM_RESET_TO_PREPARE:True})
    wait_for_ack(Var.OK,Var.ARM_RESET_TO_PREPARE, 10)

def arm_grasp_dart():
    send_kv({Var.ARM_GRASP_DART: True})
    wait_for_ack(Var.OK,Var.ARM_GRASP_DART, 10)

def arm_load_dart():
    send_kv({Var.ARM_LOAD_DART: True})
    wait_for_ack(Var.OK,Var.ARM_LOAD_DART, 30)

def arm_relax():
    send_kv({Var.ARM_RELAX: True})
    
def set_fire_speed(speed: float):
    send_kv({Var.FRICTION_WHEEL_SPEED: speed})
    
def fire_once():
    send_kv({Var.FIRE_ONCE:True})
    wait_for_ack(Var.OK,Var.FIRE_ONCE, 30)

# --- 炮台相关 ---
def set_turret_yaw(angle: float):
    # 确保角度在有效范围内
    angle = max(-1.0, min(1.0, angle))
    send_kv({Var.TURRET_ANGLE_YAW: angle})
    time.sleep(0.5)  # 等待炮台转动到位


