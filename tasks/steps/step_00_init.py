from time import time, sleep
from typing import Optional
from vision import get_vision
from core.logger import logger
from ..debug_vars_enhanced import reset_debug_vars, set_debug_var, DebugLevel, DebugCategory
from communicate import Var, send_kv, get_latest_decoded

class Step00Init:
    """
    Step 0: 初始化与自检
    - 上位机与下位机握手
    """
    def __init__(self):
        self.handshake_seq = 1

    def run(self) -> bool:
        reset_debug_vars()
        
        # 与单片机握手
        if not self._handshake_with_mcu():
            logger.error("[InitSelfcheck] 与单片机握手失败")
            set_debug_var('init_status', 'handshake_failed', DebugLevel.ERROR, DebugCategory.STATUS, "初始化握手失败")
            return False
        
        logger.info("[InitSelfcheck] 初始化完成")
        set_debug_var('init_status', 'success', DebugLevel.SUCCESS, DebugCategory.STATUS, "初始化成功完成")
        return True
    
    def _handshake_with_mcu(self) -> bool:
        """与单片机握手：发送 HEARTBEAT，等待回同值的 HEARTBEAT"""
        max_attempts = 20
        timeout = 2.0  # 2秒超时

        def _bytes_to_int_le(b: bytes) -> int:
            # HEARTBEAT 按协议是1字节；为兼容，允许1/2/4字节小端
            if not b:
                return -1
            return int.from_bytes(b, 'little', signed=False)

        for attempt in range(max_attempts):
            logger.info(f"[Handshake] 尝试第 {attempt + 1} 次握手 (HEARTBEAT={self.handshake_seq})")
            set_debug_var('handshake_attempt', attempt + 1,
                        DebugLevel.INFO, DebugCategory.STATUS, "握手尝试次数")

            # 1) 发送 HEARTBEAT（上位机发起）
            send_kv({
                Var.HEARTBEAT: self.handshake_seq  # 1字节序号
            })

            # 2) 等待 MCU 回同值 HEARTBEAT
            start_time = time()
            while time() - start_time < timeout:
                latest_data = get_latest_decoded()
                if latest_data is None:
                    sleep(0.01)
                    continue

                # 遍历已解码 TLV
                for tlv in getattr(latest_data, 'tlvs', []):
                    if tlv.t == Var.HEARTBEAT:
                        hb_value = _bytes_to_int_le(tlv.v)
                        if hb_value == (self.handshake_seq & 0xFF):
                            logger.info("[Handshake] 握手成功（收到匹配的 HEARTBEAT）")
                            set_debug_var('handshake_status', 'success',
                                        DebugLevel.SUCCESS, DebugCategory.STATUS, "与单片机握手成功")
                            return True

                sleep(0.01)

            logger.warning(f"[Handshake] 第 {attempt + 1} 次握手超时")
            # 3) 序号递增并循环到 1 字节
            self.handshake_seq = (self.handshake_seq + 1) & 0xFF
            if self.handshake_seq == 0:
                self.handshake_seq = 1
            sleep(0.1)  # 短暂等待后重试

        logger.error("[Handshake] 握手失败，已达到最大重试次数")
        set_debug_var('handshake_status', 'failed',
                    DebugLevel.ERROR, DebugCategory.STATUS, "握手失败，超过最大重试次数")
        return False