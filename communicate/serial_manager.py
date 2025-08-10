import serial
import threading
import time

class SerialManager:
    def __init__(self, port, baudrate=9600, timeout=1):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.lock = threading.Lock()
        self.running = False
        self.recv_callback = None

    def send(self, data: str):
        with self.lock:
            self.ser.write((data + '\n').encode('utf-8'))

    def set_recv_callback(self, callback):
        self.recv_callback = callback

    def start_receiving(self):
        self.running = True
        threading.Thread(target=self._receive_loop, daemon=True).start()

    def _receive_loop(self):
        while self.running:
            if self.ser.in_waiting:
                data = self.ser.readline().decode('utf-8').strip()
                if self.recv_callback:
                    self.recv_callback(data)
            time.sleep(0.01)

    def stop_receiving(self):
        self.running = False

    def close(self):
        self.ser.close()
