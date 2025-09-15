
from communicate import Var, send_kv
import time
from time import sleep
from typing import Literal


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
    


def send_gripper_tag_pos(x: float, y: float, z: float):
    send_kv({Var.GRIPPER_TAG_X: x, Var.GRIPPER_TAG_Y: y,
            Var.GRIPPER_TAG_Z: z})


def gripper_grasp():
    send_kv({Var.GRIPPER_GRASP: True})


def gripper_release():
    send_kv({Var.GRIPPER_RELEASE: True})

    
def set_fire_speed(speed: float):
    send_kv({Var.FRICTION_WHEEL_SPEED: speed})

