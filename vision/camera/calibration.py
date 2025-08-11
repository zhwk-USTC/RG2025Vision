"""
摄像头标定模块

提供摄像头标定功能，用于计算内参和畸变系数。
"""

import cv2
import numpy as np
import os
import time
from typing import List, Tuple, Optional
from .intrinsics import CameraIntrinsics
from core.logger import logger


class CameraCalibrator:
    """摄像头标定器"""
    
    def __init__(self, board_size: Tuple[int, int] = (7, 6), square_size: float = 0.025):
        """
        初始化标定器
        
        Args:
            board_size: 棋盘格角点数量 (宽, 高)
            square_size: 棋盘格方块尺寸 (m)
        """
        self.board_size = board_size
        self.square_size = square_size
        self.object_points = []  # 3D 点
        self.image_points = []   # 2D 点
        self.calibration_images = []  # 保存用于标定的图像
        self.image_size = None   # 图像尺寸
        
        # 创建棋盘格3D点
        self.objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
        self.objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2) * square_size
        
        # 角点查找参数
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        
        # 标定结果
        self.camera_matrix = None
        self.dist_coeffs = None
        self.reprojection_error = None
        self.intrinsics = None
    
    def add_calibration_image(self, image: np.ndarray) -> bool:
        """
        添加标定图像并尝试查找角点
        
        Args:
            image: 输入图像
            
        Returns:
            bool: 是否成功添加并找到角点
        """
        if image is None:
            logger.warning("无效的标定图像")
            return False
        
        # 确保图像是灰度图像
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
        gray = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
        
        # 保存图像尺寸
        if self.image_size is None:
            self.image_size = (gray.shape[1], gray.shape[0])
        elif self.image_size != (gray.shape[1], gray.shape[0]):
            logger.warning(f"图像尺寸不一致: {self.image_size} != {(gray.shape[1], gray.shape[0])}")
            return False
        
        # 查找棋盘格角点
        ret, corners = cv2.findChessboardCorners(gray, self.board_size, None)
        
        if ret:
            # 精细角点检测
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
            
            # 添加结果
            self.object_points.append(self.objp)
            self.image_points.append(corners2)
            self.calibration_images.append(image.copy())
            
            logger.info(f"成功添加标定图像: 已收集 {len(self.object_points)} 张")
            return True
        else:
            logger.warning("未能在图像中找到棋盘格角点")
            return False
    
    def calibrate(self) -> Optional[CameraIntrinsics]:
        """
        执行相机标定
        
        Returns:
            CameraIntrinsics: 标定后的相机内参，失败则返回None
        """
        if len(self.object_points) < 5:
            logger.warning(f"标定图像不足，需要至少5张，当前{len(self.object_points)}张")
            return None
        
        if self.image_size is None:
            logger.error("未设置图像尺寸")
            return None
        
        try:
            # 执行相机标定
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                self.object_points, 
                self.image_points, 
                self.image_size, 
                None, 
                None
            )
            
            if not ret:
                logger.error("相机标定失败")
                return None
            
            # 保存结果
            self.camera_matrix = mtx
            self.dist_coeffs = dist
            
            # 计算重投影误差
            mean_error = 0
            for i in range(len(self.object_points)):
                imgpoints2, _ = cv2.projectPoints(
                    self.object_points[i], rvecs[i], tvecs[i], mtx, dist
                )
                error = cv2.norm(self.image_points[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
                mean_error += error
            
            self.reprojection_error = mean_error / len(self.object_points)
            logger.info(f"相机标定完成，重投影误差: {self.reprojection_error}")
            
            # 创建内参对象
            self.intrinsics = CameraIntrinsics(
                fx=float(mtx[0, 0]),
                fy=float(mtx[1, 1]),
                cx=float(mtx[0, 2]),
                cy=float(mtx[1, 2]),
                k1=float(dist[0, 0]) if dist.size > 0 else 0.0,
                k2=float(dist[0, 1]) if dist.size > 1 else 0.0,
                p1=float(dist[0, 2]) if dist.size > 2 else 0.0,
                p2=float(dist[0, 3]) if dist.size > 3 else 0.0,
                k3=float(dist[0, 4]) if dist.size > 4 else 0.0
            )
            
            return self.intrinsics
            
        except Exception as e:
            logger.error(f"相机标定过程中出现错误: {e}")
            return None
    
    def draw_corners(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        在图像上绘制角点
        
        Args:
            image: 输入图像
            
        Returns:
            np.ndarray: 绘制角点后的图像，失败则返回None
        """
        if image is None:
            return None
        
        # 确保图像是灰度图像
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
        gray = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
        
        # 查找棋盘格角点
        ret, corners = cv2.findChessboardCorners(gray, self.board_size, None)
        
        if ret:
            # 精细角点检测
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
            
            # 绘制角点
            img_draw = image.copy()
            cv2.drawChessboardCorners(img_draw, self.board_size, corners2, ret)
            return img_draw
        else:
            return image
    
    def clear(self) -> None:
        """清空所有标定数据"""
        self.object_points = []
        self.image_points = []
        self.calibration_images = []
        self.image_size = None
        self.camera_matrix = None
        self.dist_coeffs = None
        self.reprojection_error = None
        self.intrinsics = None
        logger.info("已清空所有标定数据")
    
    def undistort_image(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        对图像进行畸变校正
        
        Args:
            image: 输入图像
            
        Returns:
            np.ndarray: 校正后的图像，失败则返回None
        """
        if image is None or self.camera_matrix is None or self.dist_coeffs is None:
            return None
        
        return cv2.undistort(image, self.camera_matrix, self.dist_coeffs)
    
    def save_intrinsics(self, file_path: str) -> bool:
        """
        保存内参到文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否成功保存
        """
        if self.intrinsics is None:
            logger.warning("没有可保存的内参")
            return False
        
        return self.intrinsics.save(file_path)
    
    def get_intrinsics(self) -> Optional[CameraIntrinsics]:
        """
        获取标定后的内参
        
        Returns:
            CameraIntrinsics: 相机内参
        """
        return self.intrinsics
