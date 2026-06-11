import time
import subprocess
import numpy as np
import cv2
import threading
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class CameraWorker(QObject):
    frame_ready = pyqtSignal(object)
    high_res_saved_notification = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self.proc = None
        self.stream_thread = None
        
        self._should_record = False 
        self.video_filepath = ""
        self.video_writer = None

    @pyqtSlot()
    def start_stream(self):
        if self.running:
            return
        self.running = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()

    def _stream_loop(self):
        print("[CAMERA] Launching native background camera pipeline...")
        cmd = [
            "rpicam-vid",
            "-t", "0",
            "--width", "1280",          
            "--height", "720",
            "--framerate", "30",
            "--codec", "mjpeg",         
            "--nopreview",
            "--rotation", "180",
            "-o", "-"
        ]
        
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            byte_buffer = b""

            for chunk in iter(lambda: self.proc.stdout.read(8192), b''):
                if not self.running:
                    break
                if not chunk: 
                    continue
                    
                byte_buffer += chunk
                a = byte_buffer.find(b'\xff\xd8') 
                b = byte_buffer.find(b'\xff\xd9') 

                if a != -1 and b != -1:
                    if a < b:
                        jpg = byte_buffer[a:b+2]
                        byte_buffer = byte_buffer[b+2:] 
                        
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            
                            if self._should_record:
                                if self.video_writer is None:
                                    h, w, _ = frame.shape
                                    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                                    self.video_writer = cv2.VideoWriter(self.video_filepath, fourcc, 30.0, (w, h))
                                
                                if self.video_writer is not None and self.video_writer.isOpened():
                                    self.video_writer.write(frame)
                            else:
                                if self.video_writer is not None:
                                    self.video_writer.release()
                                    self.video_writer = None
                                    print("[CAMERA] Video writer stream safely released.")

                            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            self.frame_ready.emit(rgb_frame)
                    else:
                        byte_buffer = byte_buffer[b+2:]
                        
        except Exception as e:
            print(f"[CAMERA SYSTEM FAULT] Video byte pipeline crashed: {e}")
        finally:
            self.cleanup()

    @pyqtSlot(str)
    def start_video_recording(self, target_filepath):
        self.video_filepath = target_filepath
        self._should_record = True 
        print(f"[CAMERA] Video target locked -> {target_filepath}")

    @pyqtSlot()
    def stop_video_recording(self):
        self._should_record = False 

    @pyqtSlot(str)
    def capture_maximum_resolution_still(self, target_filepath):
        print("[CAMERA] Engagement signal caught. Suspending preview...")
        self.stop_stream_process()
        
        if self.stream_thread is not None:
            self.stream_thread.join(timeout=2.0)
            
        time.sleep(0.5) 

        try:
            print(f"[CAMERA] Deploying high-fidelity 64MP capture...")
            capture_cmd = ["rpicam-jpeg", "-o", target_filepath, "-q", "100", "--rotation", "180"]
            subprocess.run(capture_cmd, check=True)
            self.high_res_saved_notification.emit(target_filepath)
        except Exception as e:
            print(f"[CAMERA ATTEMPT FAILURE] Hardware snap call rejected: {e}")

        print("[CAMERA] Restoring standard system workflow...")
        self.start_stream()

    def stop_stream_process(self):
        self.running = False
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                try: self.proc.kill()
                except Exception: pass
            self.proc = None

    def stop(self):
        self.stop_stream_process()

    def cleanup(self):
        self.stop_stream_process()
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None