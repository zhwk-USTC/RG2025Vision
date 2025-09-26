import cv2
import numpy as np
import time
import platform
import math
from typing import Optional, Any, Iterable
from dataclasses import dataclass

from .manager import CameraInfo, get_camera_info_list
from core.logger import logger

@dataclass(slots=True)
class CameraConfig:
    # 基础流参数
    index: int = -1
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    fourcc: Optional[str] = None      # 如 "MJPG" / "YUY2" / "H264"，None 表示不强制

    # 缓冲区（可降低延迟；并非所有后端支持）
    buffersize: Optional[int] = 1

    # 暴光相关
    auto_exposure_off: Optional[bool] = None   # True 表示尝试关闭 AE
    exposure: Optional[float] = None           # 直接写入 CAP_PROP_EXPOSURE 的值（平台相关）
    gain: Optional[float] = None               # 增益

    # 白平衡
    auto_wb_off: Optional[bool] = None         # True 表示关闭自动白平衡
    wb_temperature: Optional[int] = None       # 色温（K）


class Camera:
    """
    设备层相机：负责连接、采帧与基本参数维护。
    """

    def __init__(self, config: Optional[CameraConfig] = None) -> None:
        # 基本信息
        self.info: Optional[CameraInfo] = None
        self.connected: bool = False
        self.cap: Optional[cv2.VideoCapture] = None

        # 请求的视频参数（连接前可设置）
        self.width: Optional[int] = None       # 实际值在 connect 后回读覆盖
        self.height: Optional[int] = None
        self.fps: Optional[float] = None       # 实际值在 connect 后回读覆盖

        # 保存完整配置以用于应用专业参数
        self._config: CameraConfig = config if config else CameraConfig()

        if config:
            try:
                self.select_by_index(config.index)
            except Exception as e:
                logger.error(f"摄像头初始化失败: {e}")
                self.info = None
                return
            self.width = config.width
            self.height = config.height
            self.fps = config.fps

    # -------------------------- 连接/断开 --------------------------

    def select_by_info(self, info: CameraInfo) -> None:
        """通过 CameraInfo 选择摄像头"""
        self.info = info
        self.cap = None
        logger.info(f"{self.info.name} 已选择: {self.info.name} (index={self.info.index})")

    def select_by_index(self, camera_index: int) -> None:
        """通过索引选择摄像头"""
        cam_info_list = get_camera_info_list()
        if camera_index < 0 or camera_index >= len(cam_info_list):
            raise IndexError(f"无效的摄像头索引: {camera_index}")
        self.select_by_info(cam_info_list[camera_index])

    @property
    def is_open(self) -> bool:
        return bool(self.connected and self.cap is not None and self.cap.isOpened())

    # --------- 通用安全设置函数 ---------
    def _try_set(self, prop: int, value: float | int, name: str) -> bool:
        """set -> get 回读校验并记录日志"""
        assert self.cap is not None
        try:
            ok = self.cap.set(prop, float(value))
            r = self.cap.get(prop)
            logger.debug(f"{name}: set {value} -> read {r} (ok={ok})")
            # 某些驱动会四舍五入到最近合法值，不做苛刻等值判断
            return ok
        except Exception as e:
            logger.debug(f"{name}: 设置异常 {e}")
            return False

    def _try_set_multi(self, prop: int, values: Iterable[float | int], name: str) -> bool:
        """按顺序尝试多个取值（用于兼容不同平台语义）"""
        for v in values:
            if self._try_set(prop, v, name):
                return True
        return False

    def _supports(self, prop: int) -> bool:
        """探测某属性是否可用"""
        if self.cap is None:
            return False
        try:
            v = self.cap.get(prop)
            if v != -1 and not math.isnan(v):
                return True
        except Exception:
            pass
        try:
            ok = self.cap.set(prop, 0.0)
            v2 = self.cap.get(prop)
            return bool(ok and v2 != -1 and not math.isnan(v2))
        except Exception:
            return False

    # -------------------------- 曝光 --------------------------

    def _set_exposure_smart(self) -> None:
        """
        曝光的跨平台设置：
        - 若提供 exposure（原始值），直接写入 CAP_PROP_EXPOSURE。
        """
        AE = getattr(cv2, "CAP_PROP_AUTO_EXPOSURE", 21)

        if self._config.auto_exposure_off:
            # 不同后端语义各异：0/1 或 0.25/0.75；这里都试一下“关闭自动”
            self._try_set_multi(AE, [0, 0.25, 1], "AUTO_EXPOSURE(尝试关闭)")

        # 直接设原始曝光值
        if self._config.exposure is not None:
            self._try_set(getattr(cv2, "CAP_PROP_EXPOSURE", 15), self._config.exposure, "EXPOSURE(raw)")

        # 如果没有设置任何手动曝光参数且未明确关闭自动曝光，则恢复自动曝光
        if (not self._config.auto_exposure_off and
            self._config.exposure is None):
            # 不同后端语义各异：0.75/1 或其他值表示"开启自动"
            self._try_set_multi(AE, [0.75, 1, 3], "AUTO_EXPOSURE(恢复自动)")

        if self._config.gain is not None:
            self._try_set(getattr(cv2, "CAP_PROP_GAIN", 14), self._config.gain, "GAIN")

    # -------------------------- 白平衡 --------------------------

    def _k_to_blue_red(self, k: int, lo: int = 0, hi: int = 4096) -> tuple[int, int]:
        """
        将色温(K)近似映射为 BLUE_U / RED_V 的寄存器值（简单线性映射，不做自动求增益）。
        设定：
          - 3000K 近似为暖光：RED_V 高、BLUE_U 低
          - 6500K 近似为日光：BLUE_U 高、RED_V 适中
        """
        k = max(3000, min(6500, int(k)))
        # 归一化到 [0,1]
        t = (k - 3000) / (6500 - 3000)

        # 设 BLUE_U: 3000K -> 0.40, 6500K -> 0.65
        #    RED_V : 3000K -> 0.70, 6500K -> 0.55
        blue_norm = 0.40 + (0.65 - 0.40) * t
        red_norm  = 0.70 + (0.55 - 0.70) * t

        blue = int(lo + blue_norm * (hi - lo))
        red  = int(lo + red_norm  * (hi - lo))
        return blue, red

    def _set_white_balance_smart(self) -> None:
        """
        白平衡的跨平台设置（无自动求增益版）：
        - 若关闭自动白平衡，优先尝试设置 Kelvin 色温；
        - 若设备不支持 Kelvin，则回退到 BLUE_U/RED_V 的固定映射；
        - 若既未提供色温又关闭了自动，则把 BLUE_U/RED_V 设为中性基准。
        """
        assert self.cap is not None

        # 常量（用 getattr 兼容旧版本）
        AUTO_WB   = getattr(cv2, "CAP_PROP_AUTO_WB", 44)
        WB_TEMP   = getattr(cv2, "CAP_PROP_WB_TEMPERATURE", 45)
        WB_BLUE_U = getattr(cv2, "CAP_PROP_WHITE_BALANCE_BLUE_U", 17)
        WB_RED_V  = getattr(cv2, "CAP_PROP_WHITE_BALANCE_RED_V", 28)

        def _sleep_short(sec: float = 0.1):
            try:
                time.sleep(sec)
            except Exception:
                pass

        # 1) 如请求手动，先尝试关闭自动WB
        if self._config.auto_wb_off:
            self._try_set_multi(AUTO_WB, [0, 0.0], "AUTO_WB(尝试关闭)")
            _sleep_short(0.12)  # 给驱动切换时间

        # 2) 优先尝试 Kelvin 色温
        wrote_any = False
        has_wbt = self._supports(WB_TEMP)
        if self._config.wb_temperature is not None and has_wbt:
            target_k = int(self._config.wb_temperature)
            target_k = max(2800, min(6500, target_k))  # 保守夹取
            if self._try_set(WB_TEMP, target_k, "WB_TEMPERATURE"):
                _sleep_short(0.05)
                wrote_any = True

        # 3) Kelvin 不可用时的兜底：BLUE_U / RED_V 固定映射（不做自动求增益）
        if not wrote_any and self._config.auto_wb_off:
            has_blue = self._supports(WB_BLUE_U)
            has_red  = self._supports(WB_RED_V)

            if has_blue or has_red:
                # 若提供色温，则用映射；否则给中性基准（0.5区间）
                lo, hi = 0, 4096
                if self._config.wb_temperature is not None:
                    blue_val, red_val = self._k_to_blue_red(self._config.wb_temperature, lo, hi)
                else:
                    blue_val = (lo + hi) // 2
                    red_val  = (lo + hi) // 2

                if has_blue: self._try_set(WB_BLUE_U, blue_val, "WB_BLUE_U(兜底)")
                if has_red:  self._try_set(WB_RED_V,  red_val,  "WB_RED_V(兜底)")
                _sleep_short(0.05)
                wrote_any = True
            else:
                logger.debug("WB兜底不可用：设备不支持 WB_BLUE_U/RED_V")

        # 4) 若既没请求手动也未指定色温 → 恢复自动（有能力时）
        if (not self._config.auto_wb_off and
            self._config.wb_temperature is None and
            self._supports(AUTO_WB)):
            self._try_set_multi(AUTO_WB, [1, 0.75], "AUTO_WB(恢复自动)")

        # 能力记录
        logger.debug(
            f"WB caps -> AUTO:{self._supports(AUTO_WB)} TEMP:{self._supports(WB_TEMP)} "
            f"BLUE_U:{self._supports(WB_BLUE_U)} RED_V:{self._supports(WB_RED_V)}"
        )

    # -------------------------- 应用控制 --------------------------

    def _apply_controls(self) -> None:
        """在 connect() 成功打开后调用，按推荐顺序应用所有可选控制"""
        assert self.cap is not None

        # ---- 1) FourCC / 分辨率 / FPS / 缓冲（尽量先设）----
        if self._config.fourcc:
            try:
                fourcc = cv2.VideoWriter_fourcc(*self._config.fourcc)  # type: ignore
                self._try_set(getattr(cv2, "CAP_PROP_FOURCC", 6), fourcc, f"FOURCC({self._config.fourcc})")
            except Exception:
                logger.debug("设置 FOURCC 失败，后端可能不支持")

        if self._config.buffersize is not None:
            try:
                self._try_set(getattr(cv2, "CAP_PROP_BUFFERSIZE", 38), int(self._config.buffersize), "BUFFERSIZE")
            except Exception:
                pass

        # ---- 2) 曝光/增益（先关自动再设值）----
        self._set_exposure_smart()

        # ---- 3) 白平衡 ----
        self._set_white_balance_smart()

        # 回读并更新实际生效的宽高/FPS
        real_w = int(self.cap.get(getattr(cv2, "CAP_PROP_FRAME_WIDTH", 3))) or (self.width or 0)
        real_h = int(self.cap.get(getattr(cv2, "CAP_PROP_FRAME_HEIGHT", 4))) or (self.height or 0)
        real_fps = float(self.cap.get(getattr(cv2, "CAP_PROP_FPS", 5))) or (self.fps or 0.0)
        self.width, self.height, self.fps = real_w, real_h, real_fps

    # -------------------------- 连接 --------------------------

    def connect(self) -> bool:
        """连接设备并应用参数设置；回读实际参数"""
        if self.info is None:
            raise ValueError("请先选择摄像头（select_camera_by_index / select_camera_info）")
        if self.connected:
            logger.warning(f"摄像头 {self.info.name} 已连接")
            return True

        try:
            backend = getattr(self.info, "backend", 0)
            self.cap = cv2.VideoCapture(self.info.index, backend)
            time.sleep(0.25)  # 设备初始化等待（少量即可）

            if not self.cap.isOpened():
                raise ConnectionError(f"无法打开摄像头 {self.info.name}")

            # 优先 FourCC
            if platform.system() == "Linux":
                # 若未指定 fourcc，Linux 默认尝试 MJPG 提升带宽
                if not self._config.fourcc:
                    ok_fourcc = self.cap.set(getattr(cv2, "CAP_PROP_FOURCC", 6),
                                             cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # type: ignore
                    if not ok_fourcc:
                        logger.debug("设置 MJPG FourCC 失败，后端可能不支持")
            elif self._config.fourcc:
                # 其他平台如指定了四字符码，也尝试设置
                try:
                    self.cap.set(getattr(cv2, "CAP_PROP_FOURCC", 6),
                                 cv2.VideoWriter_fourcc(*self._config.fourcc))  # type: ignore
                except Exception:
                    logger.debug("设置 FOURCC 失败，后端可能不支持")

            # 目标分辨率/FPS（先设再回读）
            if self.width and self.height:
                ok_w = self.cap.set(getattr(cv2, "CAP_PROP_FRAME_WIDTH", 3), self.width)
                ok_h = self.cap.set(getattr(cv2, "CAP_PROP_FRAME_HEIGHT", 4), self.height)
                if not (ok_w and ok_h):
                    logger.debug("设置分辨率失败（后端可能不支持），将回读实际分辨率")

            if self.fps:
                ok_fps = self.cap.set(getattr(cv2, "CAP_PROP_FPS", 5), float(self.fps))
                if not ok_fps:
                    logger.debug("设置 FPS 失败（后端可能不支持），将回读实际 FPS")

            # 缓冲区（可选）
            if self._config.buffersize is not None:
                try:
                    self.cap.set(getattr(cv2, "CAP_PROP_BUFFERSIZE", 38), int(self._config.buffersize))
                except Exception:
                    pass

            # 读一帧热身（部分后端需先抓取帧才能应用控制）
            _ = self.cap.read()

            # 应用专业参数
            self._apply_controls()

            # 再抓一帧验证
            ret, frame = self.cap.read()
            if not ret:
                raise RuntimeError(f"摄像头 {self.info.name} 初始帧读取失败")

            # 设置状态
            self.connected = True
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            logger.info(f"已连接 {self.info.name} ({self.width}x{self.height} @ {self.fps:.1f}fps)")
            return True

        except Exception as e:
            logger.error(f"摄像头 {self.info.name} 连接失败: {e}")
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """断开设备连接并清空运行时状态"""
        try:
            if self.cap is not None:
                self.cap.release()
        finally:
            self.cap = None
        self.connected = False

        if self.info:
            logger.info(f"已断开 {self.info.name}")
        else:
            logger.info("已断开摄像头")

    # -------------------------- 采帧 --------------------------

    def read_frame(self) -> "cv2.typing.MatLike":
        """读取一帧图像，返回 RGB"""
        if not self.is_open:
            raise RuntimeError("摄像头未连接")
        ret, frame = self.cap.read()  # type: ignore[union-attr]
        if not ret:
            raise RuntimeError("读取摄像头帧失败")
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

    def get_config(self) -> CameraConfig:
        if not self.info:
            return CameraConfig()
        return CameraConfig(
            index=self.info.index,
            width=self.width if self.width else 1080,
            height=self.height if self.height else 720,
            fps=self.fps if self.fps else 30,
            fourcc=self._config.fourcc,
            buffersize=self._config.buffersize,
            auto_exposure_off=self._config.auto_exposure_off,
            exposure=self._config.exposure,
            gain=self._config.gain,
            auto_wb_off=self._config.auto_wb_off,
            wb_temperature=self._config.wb_temperature,
        )

    def __str__(self) -> str:
        return ('Camera: '+
                '\nname: '+ str(self.info.name if self.info else "未知") +
                '\nindex: '+ str(self.info.index if self.info else -1) +
                '\nconnected: '+ str(self.connected) +
                '\nwidth: '+ str(self.width) +
                '\nheight: '+ str(self.height) +
                '\nfps: '+ str(self.fps)
        )

    @property
    def name(self) -> str:
        return self.info.name if self.info else "未知"

    @property
    def index(self) -> int:
        return self.info.index if self.info else -1

    def get_status(self) -> str:
        return self.__str__()
