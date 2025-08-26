from typing import Dict

from .camera import Camera, CameraPose, CameraIntrinsics
from .config import load_camera_config, load_camera_intrinsics, load_apriltag_pose, load_camera_pose
from .tag_loc import Localization, TagPose

CAMERA_NUM = 1
cameras = [Camera() for _ in range(CAMERA_NUM)]
apriltag_map: Dict[int, TagPose] = {}

load_camera_config(cameras)
load_camera_intrinsics(cameras)
load_camera_pose(cameras)
load_apriltag_pose(apriltag_map)

localizer = Localization(
    tag_map=apriltag_map,
    camera_poses=[cam.pose for cam in cameras if cam.pose is not None]
)