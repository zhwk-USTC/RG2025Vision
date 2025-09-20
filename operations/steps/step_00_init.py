from time import time, sleep
from typing import Optional
from vision import get_vision
from core.logger import logger
from ..debug_vars_enhanced import reset_debug_vars, set_debug_var, DebugLevel, DebugCategory
from communicate import Var, send_kv, start_serial
from ..utils.communicate_utils import wait_for_ack

class Step00Init:
    """
    Step 0: 初始化与自检
    - 上位机与下位机握手
    """
    def __init__(self):
        self.handshake_seq = 1

    def run(self) -> bool:
        reset_debug_vars()
        
        # 初始化并开启串口
        logger.info("[InitSelfcheck] 初始化串口...")
        set_debug_var('serial_status', 'initializing', DebugLevel.INFO, DebugCategory.STATUS, "正在初始化串口")
        
        try:
            if not start_serial():
                logger.error("[InitSelfcheck] 串口启动失败")
                set_debug_var('serial_status', 'start_failed', DebugLevel.ERROR, DebugCategory.STATUS, "串口启动失败")
                return False
            
            logger.info("[InitSelfcheck] 串口启动成功")
            set_debug_var('serial_status', 'started', DebugLevel.SUCCESS, DebugCategory.STATUS, "串口启动成功")
        except Exception as e:
            logger.error(f"[InitSelfcheck] 串口初始化异常: {e}")
            set_debug_var('serial_status', f'error: {str(e)}', DebugLevel.ERROR, DebugCategory.STATUS, "串口初始化异常")
            return False
        
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

        for attempt in range(max_attempts):
            logger.info(f"[Handshake] 尝试第 {attempt + 1} 次握手 (HEARTBEAT={self.handshake_seq})")
            set_debug_var('handshake_attempt', attempt + 1,
                        DebugLevel.INFO, DebugCategory.STATUS, "握手尝试次数")

            # 1) 发送 HEARTBEAT（上位机发起）
            send_kv({
                Var.HEARTBEAT: self.handshake_seq  # 1字节序号
            })

            # 2) 等待 MCU 回同值 HEARTBEAT
            if wait_for_ack(Var.HEARTBEAT, self.handshake_seq & 0xFF, timeout):
                logger.info("[Handshake] 握手成功（收到匹配的 HEARTBEAT）")
                set_debug_var('handshake_status', 'success',
                            DebugLevel.SUCCESS, DebugCategory.STATUS, "与单片机握手成功")
                return True

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