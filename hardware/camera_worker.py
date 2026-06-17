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

        self._zoom_level = 1.0
        self._zoom_lock = threading.Lock()

    @pyqtSlot()
    def start_stream(self):
        if self.running:
            return
        self.running = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()

    @pyqtSlot(float)
    def set_zoom(self, zoom_level):
        with self._zoom_lock:
            self._zoom_level = max(1.0, min(4.0, zoom_level))

    def _get_zoom(self):
        with self._zoom_lock:
            return self._zoom_level

    def _apply_zoom(self, frame, zoom=None):
        if zoom is None:
            zoom = self._get_zoom()
        if zoom <= 1.0:
            return frame
        h, w = frame.shape[:2]
        new_h = int(h / zoom)
        new_w = int(w / zoom)
        start_y = (h - new_h) // 2
        start_x = (w - new_w) // 2
        cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)

    def _stream_loop(self):
        print("[CAMERA] Launching native background camera pipeline...")
        # Upgraded Stream to 1080p with HDR and Continuous Autofocus
        cmd = [
            "rpicam-vid",
            "-t", "0",
            "--width", "1920",
            "--height", "1080",
            "--framerate", "30",
            "--codec", "mjpeg",
            "-q", "95",
            "--denoise", "cdn_fast",
            "--nopreview",
            "--rotation", "180",
            "--autofocus-mode", "continuous",
            "--hdr", "single-exp",
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
                            frame = self._apply_zoom(frame)

                            if self._should_record:
                                if self.video_writer is None:
                                    fh, fw, _ = frame.shape
                                    # Switched codec to modern MP4 rendering
                                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                                    self.video_writer = cv2.VideoWriter(
                                        self.video_filepath, fourcc, 30.0, (fw, fh)
                                    )
                                if self.video_writer is not None and self.video_writer.isOpened():
                                    self.video_writer.write(frame)
                            else:
                                if self.video_writer is not None:
                                    self.video_writer.release()
                                    self.video_writer = None
                                    print("[CAMERA] Video writer released.")

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
        zoom_at_capture = self._get_zoom()

        print("[CAMERA] Suspending preview for still capture...")
        self.stop_stream_process()
        if self.stream_thread is not None:
            self.stream_thread.join(timeout=2.0)
        time.sleep(0.5)

        try:
            print(f"[CAMERA] Deploying 12MP capture (zoom={zoom_at_capture:.1f}x)...")
            tmp_path = target_filepath + ".raw_full.jpg"
            
            # Module 3 Upgrades applied here
            capture_cmd = [
                "rpicam-jpeg", "-o", tmp_path,
                "-q", "100", 
                "--rotation", "180",
                "--nopreview",
                "--autofocus-on-capture", "1",
                "--hdr", "single-exp",
                "--denoise", "cdn_hq"
            ]
            subprocess.run(capture_cmd, check=True)

            full_frame = cv2.imread(tmp_path)
            if full_frame is not None:
                zoomed_frame = self._apply_zoom(full_frame, zoom=zoom_at_capture)
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 97]
                cv2.imwrite(target_filepath, zoomed_frame, encode_params)
                print(f"[CAMERA] Zoomed still saved: {target_filepath}")
            else:
                import os
                os.rename(tmp_path, target_filepath)
                print("[CAMERA] imread failed — saved raw full-res as fallback.")

            import os
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            self.high_res_saved_notification.emit(target_filepath)

        except Exception as e:
            print(f"[CAMERA] Capture failed: {e}")

        print("[CAMERA] Restoring live preview...")
        self.start_stream()

    def stop_stream_process(self):
        self.running = False
        if self.proc:
            try:
                import signal
                import subprocess
                self.proc.send_signal(signal.SIGINT)
                try:
                    self.proc.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            finally:
                self.proc = None

    def stop(self):
        self.stop_stream_process()

    def cleanup(self):
        self.stop_stream_process()
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None