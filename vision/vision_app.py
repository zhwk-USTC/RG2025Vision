import time
import threading
from .camera import Camera, cameras
from .apriltag import tag36h11_detectors, Tag36h11Detector
from core.logger import logger

def process_camera(cam: Camera, detector: Tag36h11Detector):
    """在线程中执行的摄像头处理函数"""
    if not cam.connected:
        return
        
    try:
        frame = cam.read_frame()
        result = None
        if cam.tag36h11_enabled and frame is not None:
            result = detector.detect(frame, cam.intrinsics, 1.0)

        # 直接更新camera数据
        cam.extra_data['tag36h11_result'] = result
        cam.extra_data['tag36h11_overlay'] = detector.draw_overlay(frame, result)
        cam.extra_data['tag36h11_result_text'] = detector.get_result_text(result)
    except Exception as e:
        logger.error(f"摄像头处理异常: {e}")
        cam.extra_data['tag36h11_result'] = None

def run_vision():
    logger.info(f"视觉处理启动")
    
    while True:
        # 为每个连接的摄像头创建线程
        threads = []
        
        for i, cam in enumerate(cameras):
            if cam.connected and i < len(tag36h11_detectors):
                thread = threading.Thread(
                    target=process_camera,
                    args=(cam, tag36h11_detectors[i]),
                    daemon=True
                )
                threads.append(thread)
                thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        time.sleep(0.01)
