from operations.utils.communicate_utils import turret_set_yaw
from core.logger import logger

class TurretSetYaw:
    """设置炮台yaw角度"""

    def __init__(self, angle: float):
        self.angle = angle

    def run(self):
        logger.info(f'设置炮台yaw角度: {self.angle}')
        turret_set_yaw(self.angle)
        logger.info('炮台yaw角度设置完成')