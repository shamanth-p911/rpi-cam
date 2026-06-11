import cv2
import numpy as np
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class CameraWorker(QObject):
    frame_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.running = True
        self.process = None

    def start_stream(self):
        print("[CAMERA] Launching native Pi 5 rpicam stream pipeline...")
        
        # Command to stream raw RGB data from the camera at 640x480, 30fps straight to stdout
        cmd = [
            'rpicam-vid',
            '-t', '0',                    # Run indefinitely
            '--width', '640',
            '--height', '480',
            '--framerate', '30',
            '--codec', 'yuv420',          # Lightweight, fast format
            '-o', '-'                     # Output directly to memory pipe (stdout)
        ]

        try:
            # Start the rpicam background process
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            # Frame size calculation for YUV420 format (width * height * 1.5)
            frame_size = 640 * 480 * 3 // 2

            while self.running:
                # Read raw frame bytes from the memory pipe
                raw_data = self.process.stdout.read(frame_size)
                if len(raw_data) != frame_size:
                    QThread.msleep(10)
                    continue

                # Convert raw YUV bytes into a standard NumPy BGR image matrix
                yuv_array = np.frombuffer(raw_data, dtype=np.uint8)
                frame = cv2.cvtColor(yuv_array.reshape((480 * 3 // 2, 640)), cv2.COLOR_YUV2BGR_I420)
                
                # Convert BGR to RGB for your PyQt Layout
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.frame_ready.emit(rgb_frame)

        except Exception as e:
            print(f"[CAMERA ERROR] Native pipeline failed: {e}. Switching to stripes fallback.")
            self.run_test_pattern_loop()

    def run_test_pattern_loop(self):
        w, h = 640, 480
        step = 0
        while self.running:
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            for i in range(0, w, 40):
                color = [(i + step) % 255, 120, 240 - ((i + step) % 240)]
                cv2.rectangle(frame, (i, 0), (i + 40, h), color, -1)
            cv2.putText(frame, "HARDWARE INITIALIZING...", (160, h // 2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            self.frame_ready.emit(frame)
            step = (step + 4) % 255
            QThread.msleep(33)

    def stop(self):
        self.running = False
        if self.process:
            self.process.terminate()
            self.process.wait()
