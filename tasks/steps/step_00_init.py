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
        """与单片机握手"""
        max_attempts = 20
        timeout = 2.0  # 2秒超时
        
        for attempt in range(max_attempts):
            logger.info(f"[Handshake] 尝试第 {attempt + 1} 次握手")
            set_debug_var('handshake_attempt', attempt + 1, DebugLevel.INFO, DebugCategory.STATUS, f"握手尝试次数")
            
            # 发送握手信号
            send_kv({
                Var.SEQ: self.handshake_seq,
                Var.ACK: 0  # 发送ACK=0表示请求握手
            })
            
            # 等待响应
            start_time = time()
            while time() - start_time < timeout:
                latest_data = get_latest_decoded()
                if latest_data is None:
                    sleep(0.01)
                    continue
                    
                # 检查是否收到确认
                for tlv in latest_data.tlvs:
                    if tlv.t == Var.ACK:
                        ack_value = int.from_bytes(tlv.v, 'little')
                        if ack_value == self.handshake_seq:
                            logger.info("[Handshake] 握手成功")
                            set_debug_var('handshake_status', 'success', DebugLevel.SUCCESS, DebugCategory.STATUS, "与单片机握手成功")
                            return True
                
                sleep(0.01)
            
            logger.warning(f"[Handshake] 第 {attempt + 1} 次握手超时")
            self.handshake_seq += 1
            sleep(0.1)  # 短暂等待后重试
        
        logger.error("[Handshake] 握手失败，已达到最大重试次数")
        set_debug_var('handshake_status', 'failed', DebugLevel.ERROR, DebugCategory.STATUS, "握手失败，超过最大重试次数")
        return False