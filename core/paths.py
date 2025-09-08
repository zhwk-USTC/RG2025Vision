
import os

# 获取项目根目录：main.py 所在的目录
# 当前文件是 core/paths.py，需要向上两级到达项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 统一配置目录
CONFIG_DIR = os.path.join(PROJECT_ROOT, ".config")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# 各种文件路径
VISION_CONFIG_PATH      = os.path.join(CONFIG_DIR, "vision_config.json")
SERIAL_CONFIG_PATH      = os.path.join(CONFIG_DIR, "serial_config.json")
APRILTAG_POSE_PATH      = os.path.join(ASSETS_DIR, "apriltag_pose.json")


# 确保 .config 存在（assets 是随代码发布的，不自动创建）
os.makedirs(CONFIG_DIR, exist_ok=True)
