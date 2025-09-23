import time

class delay:
    def __init__(self, time_s:float=1.0):
        self.duration = time_s

    def run(self):
        time.sleep(self.duration)