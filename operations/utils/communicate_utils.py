from communicate import Var, send_kv, get_latest_decoded, VAR_META
from communicate.protocol.protocol_py.data import _as_float32_le, _unpack_fixed_le_int
import time
from time import sleep
from typing import Literal, Optional, Any
from communicate.protocol.protocol_py.data import DataPacket
import math

# ---- 私有辅助：根据 VAR_META 解析 ----
def _parse_value_by_meta(var: Var, raw_bytes: bytes) -> Any:
    meta = VAR_META.get(int(var))
    if not meta:
        # 尝试兜底解成整型；失败则返回 None
        try:
            return _unpack_fixed_le_int(raw_bytes)
        except Exception:
            return None

    vtype = meta.get("vtype")
    try:
        if vtype == "F32":
            return _as_float32_le(raw_bytes)
        if vtype in ["BOOL", "U8", "U16", "U32"]:
            return _unpack_fixed_le_int(raw_bytes)
        # 未知类型：兜底按整型解析
        return _unpack_fixed_le_int(raw_bytes)
    except Exception:
        return None

# ---- 私有辅助：零等待读取（获取基线值，避免陈旧命中）----
def _try_read_once(var: Var) -> Optional[Any]:
    pkt = get_latest_decoded()
    if pkt is not None and isinstance(pkt, DataPacket):
        for tlv in pkt.tlvs:
            if tlv.t == var:
                return _parse_value_by_meta(var, tlv.v)
    return None

def wait_for_ack(var: Var, expected_value: int, timeout: float = -1) -> bool:
    """
    等待指定变量的ACK确认（保持原签名与用法）
    - timeout: -1 表示无限等待；>=0 表示最大等待秒数
    - 采用“只接受新值”的策略，尽量避免命中陈旧值
    """
    # 计算截止时间；-1 表示不设截止
    deadline = None if timeout is None or timeout < 0 else (time.time() + timeout)

    # 记录发送前/刚进入时的基线值（避免用到之前的旧 ACK）
    baseline = _try_read_once(var)

    # 轮询等待，使用轻微回退的间隔
    interval = 0.05  # 50ms 起步，上限 200ms
    while True:
        pkt = get_latest_decoded()
        if pkt is not None and isinstance(pkt, DataPacket):
            for tlv in pkt.tlvs:
                if tlv.t == var:
                    val = _parse_value_by_meta(var, tlv.v)

                    # 只接受“新值”：若与基线相同则继续等
                    if baseline is not None and val == baseline:
                        continue

                    # 等值判断：整型为主，浮点给容差
                    ok = False
                    if isinstance(val, float):
                        ok = math.isclose(val, float(expected_value), rel_tol=0.0, abs_tol=1e-6)
                    else:
                        try:
                            ok = (int(val) == int(expected_value))
                        except Exception:
                            ok = False

                    if ok:
                        return True

        if deadline is not None and time.time() >= deadline:
            return False

        sleep(interval)
        interval = min(interval * 1.5, 0.2)

def wait_for_value(var: Var, timeout: float = 5.0):
    """
    等待指定变量并返回解析后的值（保持原签名与语义）
    - 解析更健壮：优先按 VAR_META，失败兜底整型
    - 严格超时：timeout <= 0 视为立刻超时
    - 不强制“只接受新值”，以免影响读取类场景
    """
    if timeout is None:
        timeout = 0.0
    start = time.time()
    deadline = start + max(0.0, timeout)

    interval = 0.05  # 轮询间隔带回退
    while True:
        pkt = get_latest_decoded()
        if pkt is not None and isinstance(pkt, DataPacket):
            for tlv in pkt.tlvs:
                if tlv.t == var:
                    return _parse_value_by_meta(var, tlv.v)

        if time.time() >= deadline:
            return None

        sleep(interval)
        interval = min(interval * 1.5, 0.2)


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
    wait_for_ack(Var.OK, int(Var.IMU_RESET))
    
def imu_get_yaw() -> Optional[float]:
    """获取IMU的yaw角度值"""
    send_kv({Var.GET_IMU_YAW: True})
    return wait_for_value(Var.IMU_YAW, timeout=5.0)



# --- 机械臂相关 ---
def arm_reset():
    """上电进入复位"""
    send_kv({Var.ARM_RESET: True})
    wait_for_ack(Var.OK, int(Var.ARM_RESET))
    
def arm_reset_to_store():
    """复位 -> 存储"""
    send_kv({Var.ARM_RESET_TO_STORE: True})
    wait_for_ack(Var.OK, int(Var.ARM_RESET_TO_STORE))

def arm_low_prepare_to_grip():
    """低位准备 -> 夹取"""
    send_kv({Var.ARM_LOW_PREPARE_TO_GRIP: True})
    wait_for_ack(Var.OK, int(Var.ARM_LOW_PREPARE_TO_GRIP))

def arm_reset_to_high_prepare():
    """复位 -> 高位准备"""
    send_kv({Var.ARM_RESET_TO_HIGH_PREPARE: True})
    wait_for_ack(Var.OK, int(Var.ARM_RESET_TO_HIGH_PREPARE))
    
def arm_reset_to_low_prepare():
    """复位 -> 低位准备"""
    send_kv({Var.ARM_RESET_TO_LOW_PREPARE: True})
    wait_for_ack(Var.OK, int(Var.ARM_RESET_TO_LOW_PREPARE))

def arm_high_prepare_to_grip():
    """高位准备 -> 夹取"""
    send_kv({Var.ARM_HIGH_PREPARE_TO_GRIP: True})
    wait_for_ack(Var.OK, int(Var.ARM_HIGH_PREPARE_TO_GRIP))

def arm_store_to_reset():
    """存储 -> 复位（返回初始状态）"""
    send_kv({Var.ARM_STORE_TO_RESET: True})
    wait_for_ack(Var.OK, int(Var.ARM_STORE_TO_RESET))

def arm_shot_to_reset():
    """射击 -> 复位（返回初始状态）"""
    send_kv({Var.ARM_SHOT_TO_RESET: True})
    wait_for_ack(Var.OK, int(Var.ARM_SHOT_TO_RESET))

def arm_high_grip_to_shot():
    """高位夹取 -> 射击"""
    send_kv({Var.ARM_HIGH_GRIP_TO_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_HIGH_GRIP_TO_SHOT))

def arm_store_to_shot():
    """存储 -> 射击"""
    send_kv({Var.ARM_STORE_TO_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_STORE_TO_SHOT))

def arm_low_grip_to_wait_shot():
    """低位夹取 -> 等待射击"""
    send_kv({Var.ARM_LOW_GRIP_TO_WAIT_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_LOW_GRIP_TO_WAIT_SHOT))

def arm_high_grip_to_wait_shot():
    """高位夹取 -> 等待射击"""
    send_kv({Var.ARM_HIGH_GRIP_TO_WAIT_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_HIGH_GRIP_TO_WAIT_SHOT))

def arm_wait_shot_to_shot():
    """等待射击 -> 射击"""
    send_kv({Var.ARM_WAIT_SHOT_TO_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_WAIT_SHOT_TO_SHOT))

def arm_high_grip_to_store():
    """高位夹取 -> 存储"""
    send_kv({Var.ARM_HIGH_GRIP_TO_STORE: True})
    wait_for_ack(Var.OK, int(Var.ARM_HIGH_GRIP_TO_STORE))

def arm_low_grip_to_store():
    """低位夹取 -> 存储"""
    send_kv({Var.ARM_LOW_GRIP_TO_STORE: True})
    wait_for_ack(Var.OK, int(Var.ARM_LOW_GRIP_TO_STORE))

def arm_low_grip_to_shot():
    """低位夹取 -> 射击"""
    send_kv({Var.ARM_LOW_GRIP_TO_SHOT: True})
    wait_for_ack(Var.OK, int(Var.ARM_LOW_GRIP_TO_SHOT))
    
def set_fire_speed(speed: float):
    send_kv({Var.FRICTION_WHEEL_SPEED: speed})
    
def fire_once():
    send_kv({Var.FIRE_ONCE:True})
    wait_for_ack(Var.OK, int(Var.FIRE_ONCE), 30)

def dart_push_once():
    """推进飞镖向前，然后回到原位"""
    send_kv({Var.DART_PUSH_ONCE: True})
    wait_for_ack(Var.OK, int(Var.DART_PUSH_ONCE))

def set_friction_wheel_speed(speed: float):
    """设置摩擦轮速度"""
    send_kv({Var.FRICTION_WHEEL_SPEED: speed})

def friction_wheel_start():
    """启动摩擦轮"""
    send_kv({Var.FRICTION_WHEEL_START: True})
    wait_for_ack(Var.OK, int(Var.FRICTION_WHEEL_START))

def friction_wheel_stop():
    """停止摩擦轮"""
    send_kv({Var.FRICTION_WHEEL_STOP: True})
    wait_for_ack(Var.OK, int(Var.FRICTION_WHEEL_STOP))

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


