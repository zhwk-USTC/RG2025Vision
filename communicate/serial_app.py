import asyncio
from .serial import AsyncSerial
from typing import Optional
from serial.tools import list_ports

_serial: AsyncSerial = AsyncSerial()
_ports = None

def get_serial() -> AsyncSerial:
    return _serial

def scan_serial_ports():
    global _ports
    _ports = list_ports.comports()
    return _ports


def init_serial(port: str = '') -> AsyncSerial:
    scan_serial_ports()
    global _serial
    _serial = AsyncSerial(port=port)
    return _serial

async def start_serial():
    global _serial
    await _serial.open()
    _serial.start_receiving()

async def stop_serial():
    global _serial
    await _serial.close()