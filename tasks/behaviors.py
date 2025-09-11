
from communicate import Var, send_kv, get_latest_decoded
import time
_seq = 0

def wait_for_ack(seq):
    while True:
        latest_data = get_latest_decoded()
        if latest_data is None:
            time.sleep(0.01)
            continue
        found_ack = False
        for tlv in latest_data.tlvs:
            if tlv.t == Var.ACK:
                ack_value = int.from_bytes(tlv.v, 'little')
                if ack_value == seq:
                    found_ack = True
                    break
        if found_ack:
            break
        time.sleep(0.01)

def base_move(forward: float, left: float) -> int:
    global _seq
    send_kv({Var.BASE_MOVE_FORWARD: forward, Var.BASE_MOVE_LEFT: left, Var.SEQ: _seq})
    return _seq

def base_rotate(yaw: float) -> int:
    global _seq
    send_kv({Var.BASE_ROTATE_YAW: yaw, Var.SEQ: _seq})
    _seq += 1
    return _seq

def send_gripper_tag_pos(x: float, y: float, z: float) -> int:
    global _seq
    send_kv({Var.GRIPPER_TAG_X: x, Var.GRIPPER_TAG_Y: y, Var.GRIPPER_TAG_Z: z, Var.SEQ: _seq})
    _seq += 1
    return _seq

def gripper_grasp() -> int:
    global _seq
    send_kv({Var.GRIPPER_GRASP: True, Var.SEQ: _seq})
    _seq += 1
    return _seq

def gripper_release() -> int:
    global _seq
    send_kv({Var.GRIPPER_RELEASE: True, Var.SEQ: _seq})
    _seq += 1
    return _seq

def set_fire_speed(speed: float) -> int:
    global _seq
    send_kv({Var.FIRE_SPEED: speed, Var.SEQ: _seq})
    _seq += 1
    return _seq

def fire_once() -> int:
    global _seq
    send_kv({Var.FIRE: True, Var.SEQ: _seq})
    _seq += 1
    return _seq