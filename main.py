import sys
import os
import time
import cv2

# Explicitly appends the project root path so internal modules import smoothly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QThread, pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

# Internal Layer Components Imports
from ui.main_view import MainView
from hardware.camera_worker import CameraWorker
from hardware.gpio_worker import GPIOWorker
from hardware.system_monitor import SystemMonitorWorker

class RpiCameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RPi Native Camera")
        self.setMinimumSize(800, 480) 
        
        # Target folder for saving captured media safely
        self.output_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            print(f"[SYSTEM] Created storage directory at: {self.output_folder}")
        
        # Core State Flags & Variables
        self.latest_raw_frame = None
        self.is_recording = False
        self.video_writer = None
        self.recording_seconds = 0
        
        # Instantiate layout configuration view
        self.main_view = MainView(self)
        self.setCentralWidget(self.main_view)
        
        self.current_mode = "Manual"
        self.main_view.update_mode_text(self.current_mode)
        
        # Setup GUI Software Recording Stopwatch Timer
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.update_recording_stopwatch)
        
        # Initialize and Start Hardware Threads
        self.init_hardware_threads()
        self.connect_ui_signals()

    def init_hardware_threads(self):
        # 1. Camera Live Video Processing Pipeline Thread
        self.camera_thread = QThread(self)
        self.camera_worker = CameraWorker()
        self.camera_worker.moveToThread(self.camera_thread)
        self.camera_thread.started.connect(self.camera_worker.start_stream)
        self.camera_worker.frame_ready.connect(self.update_video_feed)
        self.camera_thread.start()

        # 2. GPIO Interfacing Thread
        self.gpio_thread = QThread(self)
        self.gpio_worker = GPIOWorker()
        self.gpio_worker.moveToThread(self.gpio_thread)
        self.gpio_thread.started.connect(self.gpio_worker.monitor_pins)
        self.gpio_worker.rotated_clockwise.connect(self.main_view.navigate_menu_down)
        self.gpio_worker.rotated_counter_clockwise.connect(self.main_view.navigate_menu_up)
        self.gpio_worker.button_pressed.connect(self.handle_hardware_capture)
        self.gpio_thread.start()

        # 3. System Diagnostic Telemetry Thread
        self.sys_thread = QThread(self)
        self.sys_worker = SystemMonitorWorker()
        self.sys_worker.moveToThread(self.sys_thread)
        self.sys_thread.started.connect(self.sys_worker.start_monitoring)
        self.sys_worker.status_updated.connect(self.main_view.update_system_status)
        self.sys_thread.start()

    def connect_ui_signals(self):
        self.main_view.camera_btn.clicked.connect(lambda: self.capture_media("photo"))
        self.main_view.video_btn.clicked.connect(lambda: self.capture_media("video"))
        self.main_view.mode_menu.itemClicked.connect(self.handle_mode_change)

    @pyqtSlot(object)
    def update_video_feed(self, rgb_frame):
        if rgb_frame is not None and not self.main_view.feed_label.size().isEmpty():
            self.latest_raw_frame = rgb_frame.copy()
            
            # If video recording toggle is active, append live frames into our media writer pipeline
            if self.is_recording and self.video_writer is not None:
                bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
                self.video_writer.write(bgr_frame)
            
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            scaled_pixmap = QPixmap.fromImage(q_img).scaled(
                self.main_view.feed_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.main_view.feed_label.setPixmap(scaled_pixmap)

    @pyqtSlot(float, float)
    def update_system_status(self, battery_pct, storage_pct):
        self.main_view.update_system_status(battery_pct, storage_pct)

    def handle_hardware_capture(self):
        self.capture_media("photo")

    def capture_media(self, media_type):
        if media_type == "photo":
            if self.latest_raw_frame is not None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"IMG_{timestamp}.jpg"
                filepath = os.path.join(self.output_folder, filename)
                bgr_frame = cv2.cvtColor(self.latest_raw_frame, cv2.COLOR_RGB2BGR)
                cv2.imwrite(filepath, bgr_frame)
                print(f"[CAPTURE] Photo saved: captures/{filename}")
        
        elif media_type == "video":
            if not self.is_recording:
                # --- START RECORDING SEQUENCE ---
                if self.latest_raw_frame is None:
                    print("[WARNING] Cannot record video; camera feed initialization pending.")
                    return
                
                self.is_recording = True
                self.recording_seconds = 0
                
                # Configure filenames using precise timestamps
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"VID_{timestamp}.avi"
                filepath = os.path.join(self.output_folder, filename)
                
                # Instantiate standard compression codecs targeting Pi 5 architecture frames (640x480 at 30 FPS)
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                self.video_writer = cv2.VideoWriter(filepath, fourcc, 30.0, (640, 480))
                
                # UI feedback changes
                self.main_view.timer_label.setText("REC 00:00:00")
                self.main_view.timer_label.show()
                self.main_view.video_btn.setStyleSheet("background-color: #990000; border-radius: 20px; border: 4px solid #FFFFFF;")
                self.recording_timer.start(1000) # Tick every 1 second
                print(f"[VIDEO] Started recording audio-visual sequence: captures/{filename}")
            else:
                # --- STOP RECORDING SEQUENCE ---
                self.is_recording = False
                self.recording_timer.stop()
                
                if self.video_writer is not None:
                    self.video_writer.release()
                    self.video_writer = None
                
                # Reset graphical interface assets
                self.main_view.timer_label.hide()
                self.main_view.video_btn.setStyleSheet("background-color: #FF0000; border-radius: 20px; border: 2px solid #FFFFFF;")
                print("[VIDEO] Recording stopped cleanly and file committed to storage disk.")

    def update_recording_stopwatch(self):
        self.recording_seconds += 1
        # Convert seconds integer into structured format layouts (Hours:Minutes:Seconds)
        hours = self.recording_seconds // 3600
        minutes = (self.recording_seconds % 3600) // 60
        seconds = self.recording_seconds % 60
        self.main_view.timer_label.setText(f"REC {hours:02d}:{minutes:02d}:{seconds:02d}")

    def handle_mode_change(self, item):
        selection = item.text()
        if "mqtt" in selection:
            self.current_mode = f"Auto: {selection.replace('-', '')}"
        elif selection == "-manual":
            self.current_mode = "Manual"
        self.main_view.update_mode_text(self.current_mode)
        self.main_view.mode_menu.hide()

    def closeEvent(self, event):
        # Prevent file corruptions if application window drops during an open capture routine
        if self.is_recording and self.video_writer is not None:
            self.video_writer.release()
            
        print("Stopping hardware workers...")
        self.camera_worker.stop()
        self.gpio_worker.stop()
        self.sys_worker.stop()
        
        self.camera_thread.quit()
        self.gpio_thread.quit()
        self.sys_thread.quit()
        
        self.camera_thread.wait()
        self.gpio_thread.wait()
        self.sys_thread.wait()
        print("All background routines stopped safely.")
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RpiCameraApp()
    window.showFullScreen() 
    sys.exit(app.exec())
