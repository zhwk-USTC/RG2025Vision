"""
小车定位模块
通过多个摄像头检测到的AprilTag来计算小车的二维坐标和朝向
"""

import numpy as np
import json
import os
from scipy.optimize import minimize
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from core.logger import logger


@dataclass
class CameraPose:
    """摄像头在小车上的位置和姿态"""
    x: float  # 相对小车中心的x坐标 (m)
    y: float  # 相对小车中心的y坐标 (m)
    angle: float  # 相对小车前方的角度 (弧度)
    fov: float = np.pi/3  # 视场角 (弧度)
    # 摄像头内参 (用于像素坐标转换)
    fx: float = 500.0  # 焦距x
    fy: float = 500.0  # 焦距y  
    cx: float = 320.0  # 光心x
    cy: float = 240.0  # 光心y
    image_width: int = 640  # 图像宽度
    image_height: int = 480  # 图像高度


@dataclass
class TagDetection:
    """AprilTag检测结果 - 基于像素坐标"""
    tag_id: int
    camera_id: int  # 摄像头索引 (0, 1, 2)
    center_x: float  # 中心像素坐标x
    center_y: float  # 中心像素坐标y
    confidence: float = 1.0  # 检测置信度


class PixelToWorldConverter:
    """像素坐标到世界坐标转换器"""
    
    def __init__(self, tag_size: float = 0.16):
        """
        Args:
            tag_size: AprilTag的实际边长 (m)，默认16cm
        """
        self.tag_size = tag_size
    
    def pixel_to_bearing_distance(self, center_x: float, center_y: float, 
                                 camera_pose: CameraPose, 
                                 tag_size_pixels: float = None) -> Tuple[float, float]:
        """
        将像素坐标转换为方位角和距离
        
        Args:
            center_x, center_y: AprilTag中心的像素坐标
            camera_pose: 摄像头参数
            tag_size_pixels: AprilTag在图像中的像素大小（用于估计距离）
            
        Returns:
            (bearing, distance): 方位角(弧度)和距离(m)
        """
        # 计算相对光心的归一化坐标
        norm_x = (center_x - camera_pose.cx) / camera_pose.fx
        norm_y = (center_y - camera_pose.cy) / camera_pose.fy
        
        # 计算方位角（相对摄像头朝向）
        bearing = np.arctan2(norm_x, 1.0)  # 水平方向的角度
        
        # 估计距离
        if tag_size_pixels is not None and tag_size_pixels > 0:
            # 基于AprilTag在图像中的大小估计距离
            # 距离 = 实际大小 * 焦距 / 像素大小
            distance = self.tag_size * camera_pose.fx / tag_size_pixels
        else:
            # 如果没有标签大小信息，使用简单的角度-距离映射
            # 这是一个粗略估计，实际应用中需要标定
            distance = 2.0  # 默认2米距离
        
        return bearing, distance
    
    def estimate_tag_size_pixels(self, corners: List[Tuple[float, float]]) -> float:
        """
        从AprilTag的四个角点估计其在图像中的像素大小
        
        Args:
            corners: 四个角点的像素坐标 [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
            
        Returns:
            tag_size_pixels: AprilTag的平均边长（像素）
        """
        if len(corners) != 4:
            return None
        
        # 计算四条边的长度
        edge_lengths = []
        for i in range(4):
            p1 = corners[i]
            p2 = corners[(i + 1) % 4]
            length = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
            edge_lengths.append(length)
        
        # 返回平均边长
        return np.mean(edge_lengths)


@dataclass
class AprilTagPose:
    """AprilTag在场地中的位置"""
    id: int
    x: float  # 场地坐标系中的x坐标 (m)
    y: float  # 场地坐标系中的y坐标 (m)
    angle: float = 0.0  # 朝向角度 (弧度)


class RobotLocalizer:
    """小车定位器"""
    
    def __init__(self):
        self.camera_poses: List[CameraPose] = []
        self.field_tags: Dict[int, AprilTagPose] = {}
        self.last_position: Optional[Tuple[float, float, float]] = None  # (x, y, theta)
        self.converter = PixelToWorldConverter()
        
        # 定位参数
        self.max_detection_distance = 5.0  # 最大检测距离 (m)
        self.position_noise_std = 0.1  # 位置噪声标准差 (m)
        self.angle_noise_std = 0.05  # 角度噪声标准差 (rad)
        
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        config_dir = os.path.join(os.path.dirname(__file__), '../.config')
        config_path = os.path.join(config_dir, 'localization_config.json')
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 加载摄像头配置
                self.camera_poses = []
                for cam_config in config.get('cameras', []):
                    pose = CameraPose(
                        x=cam_config['x'],
                        y=cam_config['y'],
                        angle=cam_config['angle'],
                        fov=cam_config.get('fov', np.pi/3),
                        fx=cam_config.get('fx', 500.0),
                        fy=cam_config.get('fy', 500.0),
                        cx=cam_config.get('cx', 320.0),
                        cy=cam_config.get('cy', 240.0),
                        image_width=cam_config.get('image_width', 640),
                        image_height=cam_config.get('image_height', 480)
                    )
                    self.camera_poses.append(pose)
                
                # 加载场地AprilTag配置
                self.field_tags = {}
                for tag_config in config.get('field_tags', []):
                    tag = AprilTagPose(
                        id=tag_config['id'],
                        x=tag_config['x'],
                        y=tag_config['y'],
                        angle=tag_config.get('angle', 0.0)
                    )
                    self.field_tags[tag.id] = tag
                
                logger.info(f"定位配置已加载: {len(self.camera_poses)}个摄像头, {len(self.field_tags)}个标签")
                
            except Exception as e:
                logger.error(f"加载定位配置失败: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        # 默认摄像头配置 (假设小车为0.3m x 0.2m)
        self.camera_poses = [
            CameraPose(x=0.1, y=0.0, angle=0.0),      # 前摄像头
            CameraPose(x=-0.05, y=0.1, angle=np.pi/2),  # 左摄像头
            CameraPose(x=-0.05, y=-0.1, angle=-np.pi/2), # 右摄像头
        ]
        
        # 默认场地标签配置 (示例)
        self.field_tags = {
            0: AprilTagPose(0, 0.0, 0.0),
            1: AprilTagPose(1, 2.0, 0.0),
            2: AprilTagPose(2, 2.0, 2.0),
            3: AprilTagPose(3, 0.0, 2.0),
        }
        
        self.save_config()
    
    def save_config(self):
        """保存配置文件"""
        config_dir = os.path.join(os.path.dirname(__file__), '../.config')
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, 'localization_config.json')
        
        config = {
            'cameras': [
                {
                    'x': pose.x,
                    'y': pose.y,
                    'angle': pose.angle,
                    'fov': pose.fov,
                    'fx': pose.fx,
                    'fy': pose.fy,
                    'cx': pose.cx,
                    'cy': pose.cy,
                    'image_width': pose.image_width,
                    'image_height': pose.image_height
                }
                for pose in self.camera_poses
            ],
            'field_tags': [
                {
                    'id': tag.id,
                    'x': tag.x,
                    'y': tag.y,
                    'angle': tag.angle
                }
                for tag in self.field_tags.values()
            ]
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"定位配置已保存到: {config_path}")
        except Exception as e:
            logger.error(f"保存定位配置失败: {e}")
    
    def add_camera_pose(self, x: float, y: float, angle: float, fov: float = np.pi/3):
        """添加摄像头位置"""
        pose = CameraPose(x, y, angle, fov)
        self.camera_poses.append(pose)
        logger.info(f"添加摄像头位置: ({x:.3f}, {y:.3f}), 角度: {angle:.3f}")
    
    def add_field_tag(self, tag_id: int, x: float, y: float, angle: float = 0.0):
        """添加场地标签"""
        tag = AprilTagPose(tag_id, x, y, angle)
        self.field_tags[tag_id] = tag
        logger.info(f"添加场地标签 {tag_id}: ({x:.3f}, {y:.3f})")
    
    def localize_from_pixels(self, pixel_detections: List[Tuple[int, int, float, float, List[Tuple[float, float]]]]) -> Optional[Tuple[float, float, float]]:
        """
        根据像素坐标检测结果定位小车
        
        Args:
            pixel_detections: 检测结果列表 [(tag_id, camera_id, center_x, center_y, corners), ...]
            corners: 可选的四个角点坐标，用于估计距离
            
        Returns:
            (x, y, theta): 小车在场地坐标系中的位置和朝向，如果定位失败返回None
        """
        if not pixel_detections:
            return None
        
        # 转换像素检测为TagDetection格式，并计算距离和方位角
        detections = []
        for detection_data in pixel_detections:
            if len(detection_data) >= 4:
                tag_id, camera_id, center_x, center_y = detection_data[:4]
                corners = detection_data[4] if len(detection_data) > 4 else None
                
                if (tag_id in self.field_tags and 
                    camera_id < len(self.camera_poses)):
                    
                    camera_pose = self.camera_poses[camera_id]
                    
                    # 估计AprilTag在图像中的大小
                    tag_size_pixels = None
                    if corners and len(corners) == 4:
                        tag_size_pixels = self.converter.estimate_tag_size_pixels(corners)
                    
                    # 转换为方位角和距离
                    bearing, distance = self.converter.pixel_to_bearing_distance(
                        center_x, center_y, camera_pose, tag_size_pixels
                    )
                    
                    if distance <= self.max_detection_distance:
                        # 创建TagDetection但用于内部处理
                        detection = {
                            'tag_id': tag_id,
                            'camera_id': camera_id,
                            'distance': distance,
                            'bearing': bearing,
                            'confidence': 1.0
                        }
                        detections.append(detection)
        
        if not detections:
            logger.warning("没有足够的有效检测结果进行定位")
            return None
        
        # 使用优化方法求解位置
        return self._optimize_position_from_dict(detections)
    
    def localize_from_detections(self, pixel_detections: List[Tuple[int, int, float, float, List[Tuple[float, float]]]]) -> Optional[Tuple[float, float, float]]:
        """
        从已经包含位姿信息的检测结果进行定位（更高效的方法）
        
        Args:
            pixel_detections: 检测结果列表，但会使用AprilTag模块计算的位姿
            
        Returns:
            (x, y, theta): 小车在场地坐标系中的位置和朝向
        """
        from vision.apriltag import AprilTagDetector
        from vision.camera import cameras
        
        detections = []
        detector = AprilTagDetector()
        
        # 对每个摄像头重新计算位姿
        for camera_id, cam in enumerate(cameras):
            if not cam.connected or camera_id >= len(self.camera_poses):
                continue
            
            frame = cam.read_frame()
            if frame is None:
                continue
            
            camera_pose = self.camera_poses[camera_id]
            camera_params = (camera_pose.fx, camera_pose.fy, camera_pose.cx, camera_pose.cy)
            
            try:
                # 使用AprilTag模块直接获取位姿
                tag_results = detector.detect_with_pose(
                    frame, 
                    camera_params=camera_params, 
                    tag_size=self.converter.tag_size
                )
                
                for tag_result in tag_results:
                    tag_id = tag_result['id']
                    if tag_id in self.field_tags:
                        detection = {
                            'tag_id': tag_id,
                            'camera_id': camera_id,
                            'distance': tag_result['distance'],
                            'bearing': tag_result['bearing'],
                            'confidence': tag_result['confidence']
                        }
                        
                        if detection['distance'] <= self.max_detection_distance:
                            detections.append(detection)
            
            except ValueError as e:
                logger.warning(f"摄像头 {camera_id} 位姿计算失败: {e}")
                continue
            except Exception as e:
                logger.error(f"摄像头 {camera_id} 处理异常: {e}")
                continue
        
        if not detections:
            logger.warning("没有足够的有效检测结果进行定位")
            return None
        
        # 使用优化方法求解位置
        return self._optimize_position_from_dict(detections)
    
    def _optimize_position_from_dict(self, detections: List[dict]) -> Optional[Tuple[float, float, float]]:
        """
        根据检测字典优化求解位置
        
        Args:
            detections: 检测字典列表
            
        Returns:
            (x, y, theta): 小车位置和朝向
        """
        if not detections:
            return None
        
        # 构建目标函数
        def objective(pose):
            x, y, theta = pose
            error = 0.0
            
            for detection in detections:
                # 获取检测信息
                tag_id = detection['tag_id']
                camera_id = detection['camera_id']
                measured_distance = detection['distance']
                measured_bearing = detection['bearing']
                confidence = detection.get('confidence', 1.0)
                
                # 计算预期的观测值
                expected_distance, expected_bearing = self._calculate_expected_observation(
                    x, y, theta, camera_id, tag_id
                )
                
                if expected_distance is not None:
                    # 计算误差
                    distance_error = (measured_distance - expected_distance) ** 2
                    bearing_error = self._angle_diff(measured_bearing, expected_bearing) ** 2
                    
                    # 考虑置信度
                    error += confidence * (distance_error + bearing_error * 10)
            
            return error
        
        # 使用多个初始猜测
        best_result = None
        best_error = float('inf')
        
        initial_guesses = [
            (0.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (-1.0, 1.0, np.pi/2),
            (1.0, -1.0, np.pi),
            (-1.0, -1.0, -np.pi/2)
        ]
        
        for initial_guess in initial_guesses:
            try:
                result = minimize(objective, initial_guess, method='BFGS')
                if result.success and result.fun < best_error:
                    best_error = result.fun
                    best_result = result.x
            except Exception as e:
                logger.warning(f"优化过程中出现错误: {e}")
                continue
        
        if best_result is not None:
            x, y, theta = best_result
            # 规范化角度
            theta = (theta + np.pi) % (2 * np.pi) - np.pi
            self.last_position = (x, y, theta)
            return (float(x), float(y), float(theta))
        
        return None                                                                     
    
    def _optimize_position(self, detections: List[TagDetection]) -> Optional[Tuple[float, float, float]]:
        """使用非线性优化求解小车位置"""
        
        # 初始猜测
        if self.last_position is not None:
            x0 = self.last_position
        else:
            # 使用第一个检测结果作为初始猜测
            first_detection = detections[0]
            tag = self.field_tags[first_detection.tag_id]
            camera = self.camera_poses[first_detection.camera_id]
            
            # 粗略估计位置
            est_x = tag.x - first_detection.distance * np.cos(first_detection.bearing)
            est_y = tag.y - first_detection.distance * np.sin(first_detection.bearing)
            est_theta = 0.0
            x0 = (est_x, est_y, est_theta)
        
        # 定义目标函数
        def objective(params):
            x, y, theta = params
            total_error = 0.0
            
            for detection in detections:
                # 计算理论检测结果
                predicted_distance, predicted_bearing = self._predict_detection(
                    x, y, theta, detection.tag_id, detection.camera_id
                )
                
                if predicted_distance is None:
                    continue
                
                # 计算误差
                distance_error = (detection.distance - predicted_distance) ** 2
                bearing_error = self._angle_diff(detection.bearing, predicted_bearing) ** 2
                
                # 加权误差
                weight = detection.confidence
                total_error += weight * (distance_error + bearing_error * 10)  # 角度误差权重更高
            
            return total_error
        
        # 优化求解
        try:
            result = minimize(
                objective,
                x0,
                method='L-BFGS-B',
                options={'maxiter': 100}
            )
            
            if result.success:
                x, y, theta = result.x
                # 归一化角度
                theta = self._normalize_angle(theta)
                
                self.last_position = (x, y, theta)
                logger.debug(f"定位成功: ({x:.3f}, {y:.3f}), 朝向: {theta:.3f}")
                return (x, y, theta)
            else:
                logger.warning(f"定位优化失败: {result.message}")
                return None
                
        except Exception as e:
            logger.error(f"定位计算异常: {e}")
            return None
    
    def _predict_detection(self, robot_x: float, robot_y: float, robot_theta: float,
                          tag_id: int, camera_id: int) -> Tuple[Optional[float], Optional[float]]:
        """预测在给定机器人位置时，摄像头应该检测到的距离和方位角"""
        
        if tag_id not in self.field_tags or camera_id >= len(self.camera_poses):
            return None, None
        
        tag = self.field_tags[tag_id]
        camera = self.camera_poses[camera_id]
        
        # 计算摄像头在场地坐标系中的位置
        cos_theta = np.cos(robot_theta)
        sin_theta = np.sin(robot_theta)
        
        camera_x = robot_x + camera.x * cos_theta - camera.y * sin_theta
        camera_y = robot_y + camera.x * sin_theta + camera.y * cos_theta
        camera_theta = robot_theta + camera.angle
        
        # 计算相对位置
        dx = tag.x - camera_x
        dy = tag.y - camera_y
        
        # 计算距离
        distance = np.sqrt(dx**2 + dy**2)
        
        # 计算相对摄像头的方位角
        tag_angle = np.arctan2(dy, dx)
        bearing = self._normalize_angle(tag_angle - camera_theta)
        
        return distance, bearing
    
    def get_position_uncertainty(self, detections: List[TagDetection]) -> Optional[Tuple[float, float, float]]:
        """估计定位不确定性"""
        if not self.last_position:
            return None
        
        # 简单的不确定性估计：基于检测数量和距离
        num_detections = len(detections)
        avg_distance = np.mean([d.distance for d in detections]) if detections else 5.0
        
        # 不确定性随检测数量减少和距离增加而增大
        pos_uncertainty = self.position_noise_std * (3.0 / max(num_detections, 1)) * (avg_distance / 2.0)
        angle_uncertainty = self.angle_noise_std * (2.0 / max(num_detections, 1))
        
        return (pos_uncertainty, pos_uncertainty, angle_uncertainty)
    
    def _calculate_expected_observation(self, robot_x: float, robot_y: float, robot_theta: float,
                                       camera_id: int, tag_id: int) -> Tuple[Optional[float], Optional[float]]:
        """计算在给定机器人位置时，摄像头应该检测到的距离和方位角"""
        
        if tag_id not in self.field_tags or camera_id >= len(self.camera_poses):
            return None, None
        
        tag = self.field_tags[tag_id]
        camera = self.camera_poses[camera_id]
        
        # 计算摄像头在世界坐标系中的位置
        cos_theta = np.cos(robot_theta)
        sin_theta = np.sin(robot_theta)
        
        cam_world_x = robot_x + camera.x * cos_theta - camera.y * sin_theta
        cam_world_y = robot_y + camera.x * sin_theta + camera.y * cos_theta
        cam_world_angle = robot_theta + camera.angle
        
        # 计算标签相对于摄像头的位置
        tag_rel_x = tag.x - cam_world_x
        tag_rel_y = tag.y - cam_world_y
        
        # 计算距离
        distance = np.sqrt(tag_rel_x**2 + tag_rel_y**2)
        
        # 计算相对于摄像头坐标系的方位角
        tag_angle_world = np.arctan2(tag_rel_y, tag_rel_x)
        bearing = self._normalize_angle(tag_angle_world - cam_world_angle)
        
        return distance, bearing
    
    def _angle_diff(self, angle1: float, angle2: float) -> float:
        """计算角度差，结果在[-π, π]范围内"""
        diff = angle1 - angle2
        return self._normalize_angle(diff)
    
    def _normalize_angle(self, angle: float) -> float:
        """将角度规范化到[-π, π]范围"""
        return (angle + np.pi) % (2 * np.pi) - np.pi


# 全局定位器实例
robot_localizer = RobotLocalizer()


def update_localization_from_cameras():
    """从摄像头数据更新定位信息（使用AprilTag模块的位姿计算）"""
    from vision.camera import cameras
    from vision.apriltag import AprilTagDetector
    
    pixel_detections = []
    
    # 创建AprilTag检测器
    detector = AprilTagDetector()
    
    # 遍历所有摄像头，提取AprilTag检测结果
    for i, cam in enumerate(cameras):
        if not cam.connected:
            continue
        
        # 获取当前帧
        frame = cam.read_frame()
        if frame is None:
            continue
        
        # 获取摄像头内参
        camera_pose = robot_localizer.camera_poses[i] if i < len(robot_localizer.camera_poses) else None
        if camera_pose is None:
            logger.warning(f"摄像头 {i} 没有配置信息，跳过")
            continue
        
        camera_params = (camera_pose.fx, camera_pose.fy, camera_pose.cx, camera_pose.cy)
        
        try:
            # 使用AprilTag模块检测并计算位姿
            tag_results = detector.detect_with_pose(
                frame, 
                camera_params=camera_params, 
                tag_size=robot_localizer.converter.tag_size
            )
            
            for tag_result in tag_results:
                # tag_result已经包含: {'id', 'center', 'corners', 'distance', 'bearing', 'confidence'}
                tag_id = tag_result['id']
                distance = tag_result['distance']
                bearing = tag_result['bearing']
                confidence = tag_result['confidence']
                
                # 创建检测数据用于定位
                detection = {
                    'tag_id': tag_id,
                    'camera_id': i,
                    'distance': distance,
                    'bearing': bearing,
                    'confidence': confidence
                }
                
                # 转换为像素检测格式以兼容现有接口
                center_x, center_y = tag_result['center']
                corners = tag_result['corners']
                pixel_detection = (tag_id, i, center_x, center_y, corners)
                pixel_detections.append(pixel_detection)
        
        except ValueError as e:
            logger.warning(f"摄像头 {i} 参数验证失败: {e}")
            continue
        except Exception as e:
            logger.error(f"摄像头 {i} 处理异常: {e}")
            continue
    
    # 执行基于像素的定位（但实际使用已计算的位姿）
    position = robot_localizer.localize_from_detections(pixel_detections)
    
    if position:
        x, y, theta = position
        logger.debug(f"小车位置更新: ({x:.3f}, {y:.3f}), 朝向: {np.degrees(theta):.1f}°")
        
        # 将结果存储到全局定位器供其他模块使用
        robot_localizer.last_position = position
        
    return position
