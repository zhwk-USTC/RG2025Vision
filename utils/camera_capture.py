import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from cv2_enumerate_cameras import enumerate_cameras
from cv2_enumerate_cameras.camera_info import CameraInfo

class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title('摄像头拍照')
        self.cap = None
        self.frame = None
        self.camera_index = tk.StringVar(value='0')
        self.resolution = tk.StringVar(value='640x480')
        self.is_running = False

        # 获取摄像头信息
        self.cameras = enumerate_cameras()
        cam_choices = [f'CAM{cam.index}: {cam.name}' for cam in self.cameras]
        cam_indices = [str(cam.index) for cam in self.cameras]
        if not cam_choices:
            cam_choices = ['0']
            cam_indices = ['0']

        # 顶部菜单栏 Frame
        self.top_frame = tk.Frame(master)
        self.top_frame.grid(row=0, column=0, sticky='ew', columnspan=7)

        # 摄像头选择
        tk.Label(self.top_frame, text='摄像头:').grid(row=0, column=0)
        self.index_box = ttk.Combobox(self.top_frame, textvariable=self.camera_index, values=cam_choices, width=25, state='readonly')
        self.index_box.grid(row=0, column=1)
        self.index_box.current(0)

        # 分辨率选择
        tk.Label(self.top_frame, text='分辨率:').grid(row=0, column=2)
        self.res_box = ttk.Combobox(self.top_frame, textvariable=self.resolution, values=['640x480','800x600','1280x720','1920x1080'], width=10)
        self.res_box.grid(row=0, column=3)

        # 按钮
        self.open_btn = tk.Button(self.top_frame, text='打开摄像头', command=self.open_camera)
        self.open_btn.grid(row=0, column=4)
        self.capture_btn = tk.Button(self.top_frame, text='拍照', command=self.capture, state='disabled')
        self.capture_btn.grid(row=0, column=5)
        self.close_btn = tk.Button(self.top_frame, text='关闭摄像头', command=self.close_camera)
        self.close_btn.grid(row=0, column=6)

        # 图像显示
        self.img_label = tk.Label(master)
        self.img_label.grid(row=1, column=0, columnspan=7)

    def open_camera(self):
        # 获取选中的摄像头 index
        idx = 0
        if self.cameras:
            sel = self.index_box.current()
            idx = self.cameras[sel].index
        else:
            idx = int(self.camera_index.get())
        res = self.resolution.get()
        w, h = map(int, res.split('x'))
        self.cap = cv2.VideoCapture(idx)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self.is_running = True
        self.capture_btn.config(state='normal')
        self.update_frame()

    def update_frame(self):
        if self.cap and self.is_running:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                # 缩放到最大640x480，保持长宽比
                max_w, max_h = 640, 480
                w, h = img.size
                if w > max_w or h > max_h:
                    scale = min(max_w / w, max_h / h)
                    new_size = (int(w * scale), int(h * scale))
                    img = img.resize(new_size)
                imgtk = ImageTk.PhotoImage(image=img)
                self.imgtk = imgtk
                self.img_label.config(image=imgtk)
            self.master.after(30, self.update_frame)

    def capture(self):
        import os
        import datetime
        if self.frame is not None:
            # 保存到 captured_images 文件夹
            save_dir = os.path.join(os.path.dirname(__file__), 'captured_images')
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            # 获取当前摄像头 index
            idx = 0
            if self.cameras:
                sel = self.index_box.current()
                idx = self.cameras[sel].index
            else:
                idx = self.camera_index.get()
            save_path = os.path.join(save_dir, f'cam{idx}_{timestamp}.jpg')
            cv2.imwrite(save_path, self.frame)
            print(f'已保存为 {save_path}')

    def close_camera(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.img_label.config(image='')
        self.capture_btn.config(state='disabled')

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry('680x540')  # 限制窗口大小
    root.resizable(False, False)  # 禁止缩放
    app = CameraApp(root)
    root.mainloop()
