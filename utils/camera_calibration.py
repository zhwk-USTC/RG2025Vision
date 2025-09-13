"""
摄像头标定工具

这是一个独立的标定程序，可以与主程序分开运行，用于标定摄像头参数。
使用方法：
- 运行程序: python calibration.py --image_dir 图片文件夹路径
- 程序将自动读取文件夹中的图片进行标定
- 标定结果将保存到指定文件
"""

import os
import sys
import time
import json
import argparse
import numpy as np
import cv2
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Dict, Any


@dataclass(slots=True)
class CameraIntrinsics:
    """摄像头内参类
    
    代表摄像头的内部参数，包括:
    - 焦距 (fx, fy)
    - 光学中心点 (cx, cy)
    - 畸变系数 (k1, k2, p1, p2, k3)
    - 图像尺寸 (用于计算FOV)
    """
    width: int
    height: int
    
    fx: float  # 焦距x
    fy: float  # 焦距y
    cx: float  # 光学中心x
    cy: float  # 光学中心y
    # 畸变系数
    k1: float = 0.0
    k2: float = 0.0
    p1: float = 0.0
    p2: float = 0.0
    k3: float = 0.0

# ====== 内参文件操作 ======

def save_intrinsics(intrinsics: CameraIntrinsics, file_path: str) -> bool:
    """保存相机内参到文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # 将对象转换为字典并保存
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(intrinsics), f, indent=2)
        
        print(f"相机内参已保存到 {file_path}")
        return True
    except Exception as e:
        print(f"保存相机内参失败: {e}")
        return False

# ====== 标定器类 ======

class CameraCalibrator:
    """摄像头标定器"""
    
    def __init__(self, board_size: Tuple[int, int] = (7, 6)):
        """
        初始化标定器
        Args:
            board_size: 棋盘格角点数量 (宽, 高)
        """
        self.board_size = board_size
        self.object_points = []  # 3D 点
        self.image_points = []   # 2D 点
        self.calibration_images = []  # 保存用于标定的图像
        self.image_size = None   # 图像尺寸

        # 创建棋盘格3D点（单位为像素，无需物理尺寸）
        self.objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
        self.objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)

        # 角点查找参数
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        # 标定结果
        self.camera_matrix = None
        self.dist_coeffs = None
        self.reprojection_error = None
        self.intrinsics = None
    
    def add_calibration_image(self, image: np.ndarray) -> bool:
        """添加标定图像并尝试查找角点"""
        if image is None:
            print("无效的标定图像")
            return False
        
        # 确保图像是灰度图像
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
        gray = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
        
        # 保存图像尺寸
        if self.image_size is None:
            self.image_size = (gray.shape[1], gray.shape[0])
        elif self.image_size != (gray.shape[1], gray.shape[0]):
            print(f"图像尺寸不一致: {self.image_size} != {(gray.shape[1], gray.shape[0])}")
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
            
            print(f"成功添加标定图像: 已收集 {len(self.object_points)} 张")
            return True
        else:
            print("未能在图像中找到棋盘格角点")
            return False
    
    def calibrate(self) -> Optional[CameraIntrinsics]:
        """执行相机标定"""
        if len(self.object_points) < 5:
            print(f"标定图像不足，需要至少5张，当前{len(self.object_points)}张")
            return None
        
        if self.image_size is None:
            print("未设置图像尺寸")
            return None
        
        try:
            # 执行相机标定
            camera_matrix = np.zeros((3, 3), np.float64)
            # OpenCV 需要初始化的畸变系数，但返回的可能是不同形状
            dist_coeffs = np.zeros(5, np.float64)  # 使用一维数组
            
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                self.object_points, 
                self.image_points, 
                self.image_size, 
                camera_matrix, 
                dist_coeffs
            )
            
            if not ret:
                print("相机标定失败")
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
            print(f"相机标定完成，重投影误差: {self.reprojection_error}")
            
            # 创建内参对象
            width, height = self.image_size
            
            # 安全获取畸变系数，确保数组索引不会超出范围
            dist_flat = dist.flatten() if dist is not None else np.zeros(5)
            
            self.intrinsics = CameraIntrinsics(
                width=width,
                height=height,
                fx=float(mtx[0, 0]),
                fy=float(mtx[1, 1]),
                cx=float(mtx[0, 2]),
                cy=float(mtx[1, 2]),
                k1=float(dist_flat[0]) if dist_flat.size > 0 else 0.0,
                k2=float(dist_flat[1]) if dist_flat.size > 1 else 0.0,
                p1=float(dist_flat[2]) if dist_flat.size > 2 else 0.0,
                p2=float(dist_flat[3]) if dist_flat.size > 3 else 0.0,
                k3=float(dist_flat[4]) if dist_flat.size > 4 else 0.0
            )
            
            return self.intrinsics
            
        except Exception as e:
            print(f"相机标定过程中出现错误: {e}")
            return None
    
    def draw_corners(self, image: np.ndarray) -> Optional[np.ndarray]:
        """在图像上绘制角点"""
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
        print("已清空所有标定数据")
    
    def undistort_image(self, image: np.ndarray) -> Optional[np.ndarray]:
        """对图像进行畸变校正"""
        if image is None or self.camera_matrix is None or self.dist_coeffs is None:
            return None
        
        return cv2.undistort(image, self.camera_matrix, self.dist_coeffs)


# ====== 主程序 ======


def process_image_folder(folder_path, calibrator: CameraCalibrator, output_file=None):
    """处理图片文件夹中的所有图片进行标定"""
    # 支持的图片文件扩展名
    valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    image_files = []
    
    # 获取所有图片文件
    for file in os.listdir(folder_path):
        ext = os.path.splitext(file)[1].lower()
        if ext in valid_extensions:
            image_files.append(os.path.join(folder_path, file))
    
    if not image_files:
        print(f"在文件夹 {folder_path} 中未找到有效的图片文件")
        return False
    
    print(f"在 {folder_path} 中找到 {len(image_files)} 个图片文件")
    
    # 处理每张图片
    for img_file in image_files:
        try:
            # 读取图片
            img = cv2.imread(img_file)
            if img is None:
                print(f"无法读取图片: {img_file}")
                continue
            
            # 添加到标定器
            success = calibrator.add_calibration_image(img)
            if success:
                print(f"成功添加图片: {os.path.basename(img_file)}")
            else:
                print(f"未在图片中找到棋盘格角点: {os.path.basename(img_file)}")
        
        except Exception as e:
            print(f"处理图片 {img_file} 时出错: {e}")
    
    # 执行标定
    if len(calibrator.image_points) < 5:
        print(f"有效的标定图片不足，需要至少5张，当前只有{len(calibrator.image_points)}张")
        return False
    
    # 执行标定
    intrinsics = calibrator.calibrate()
    if intrinsics is None:
        print("标定失败")
        return False
    
    # 显示标定结果
    print(f"标定成功！")
    print(f"图像尺寸: {intrinsics.width}x{intrinsics.height}")
    print(f"fx={intrinsics.fx:.2f}, fy={intrinsics.fy:.2f}")
    print(f"cx={intrinsics.cx:.2f}, cy={intrinsics.cy:.2f}")
    print(f"k1={intrinsics.k1:.6f}, k2={intrinsics.k2:.6f}")
    print(f"p1={intrinsics.p1:.6f}, p2={intrinsics.p2:.6f}, k3={intrinsics.k3:.6f}")
    print(f"重投影误差: {calibrator.reprojection_error}")
    
    # 保存结果
    if output_file is None:
        # 如果没有指定输出文件，使用默认路径并添加时间戳
        config_dir = os.path.join(os.path.dirname(__file__), '.config')
        os.makedirs(config_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(config_dir, f'camera_intrinsics_{timestamp}.json')
    
    # 保存内参
    save_intrinsics(intrinsics, output_file)
    print(f"已将标定结果保存至: {output_file}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='摄像头标定工具\n\n'
                    '使用示例:\n'
                    '  python camera_calibration.py -i captured_images\n'
                    '  python camera_calibration.py -i captured_images -w 9 --height 7\n'
                    '  python camera_calibration.py -i captured_images -o my_intrinsics.json\n',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-i', '--input', '--dir', '--image_dir', 
                        dest='image_dir',
                        type=str, required=True, 
                        help='标定图片文件夹路径，直接指向包含标定图片的文件夹')
    parser.add_argument('-o', '--output', '--output_path', 
                        dest='output_path',
                        type=str, 
                        help='输出内参文件路径 (默认: .config/camera_intrinsics_YYYYMMDD_HHMMSS.json)')
    parser.add_argument('--width', '--board_width', 
                        dest='board_width',
                        type=int, default=9, 
                        help='棋盘格宽度（内部角点数，默认: 9）')
    parser.add_argument('--height', '--board_height', 
                        dest='board_height',
                        type=int, default=7, 
                        help='棋盘格高度（内部角点数，默认: 7）')

    # 解析命令行参数
    args = parser.parse_args()

    # 检查图片文件夹是否存在
    image_dir = args.image_dir
    if not os.path.isdir(image_dir):
        print(f"错误: 图片文件夹不存在: {image_dir}")
        print(f"请使用 -i 或 --input 指定有效的图片文件夹路径")
        return 1

    print(f"开始对文件夹 {image_dir} 进行标定")

    # 创建输出文件路径
    if args.output_path is not None:
        output_file = args.output_path
    else:
        config_dir = os.path.join(os.path.dirname(__file__), '.config')
        os.makedirs(config_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(config_dir, f'camera_intrinsics_{timestamp}.json')

    print(f"将保存标定结果到: {output_file}")

    # 创建标定器并处理图片文件夹
    calibrator = CameraCalibrator(
        board_size=(args.board_width, args.board_height)
    )

    success = process_image_folder(image_dir, calibrator, output_file)

    print(f"\n===== 标定过程完成 =====")
    if success:
        print("标定成功")
        return 0
    else:
        print("标定失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
