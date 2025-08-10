import time
from .camera import Camera, cameras
from .apriltag import tag36h11_detectors

def run_vision():
    while True:
        if cameras[0].connected:
            # 读取摄像头帧数据
            frame = cameras[0].read_frame()
            result = None
            if(cameras[0].tag36h11_enabled and frame is not None):
                result = tag36h11_detectors[0].detect(frame)
            cameras[0].extra_data['tag36h11_result'] = result
            cameras[0].extra_data['tag36h11_overlay'] = tag36h11_detectors[0].draw_overlay(frame, result)
            cameras[0].extra_data['tag36h11_result_text'] = tag36h11_detectors[0].get_result_text(result)

        # 处理帧数据
        time.sleep(0.01)
