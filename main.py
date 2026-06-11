import sys
import os
import time
import cv2
import glob  # <--- NEW: Required for finding the newest file

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt6.QtCore import QThread, pyqtSlot, pyqtSignal, Qt, QTimer, QUrl
from PyQt6.QtGui import QImage, QPixmap, QShortcut, QKeySequence, QDesktopServices

from ui.main_view import MainView
from hardware.camera_worker import CameraWorker
from hardware.gpio_worker import GPIOWorker
from hardware.system_monitor import SystemMonitorWorker

print("[SYSTEM] Booting up Arducam Dashboard...")

class RpiCameraApp(QMainWindow):
    request_high_res_capture = pyqtSignal(str)
    request_video_start = pyqtSignal(str)
    request_video_stop = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RPi Arducam 64MP Dashboard")
        self.setMinimumSize(800, 480) 
        
        self.output_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            print(f"[SYSTEM] Created storage folder layout at: {self.output_folder}")
        
        self.latest_raw_frame = None
        self.is_recording = False
        self.recording_seconds = 0
        
        self.main_view = MainView(self)
        self.setCentralWidget(self.main_view)
        
        self.current_mode = "Manual"
        self.main_view.update_mode_text(self.current_mode)
        
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.update_recording_stopwatch)
        
        self.quit_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.quit_shortcut.activated.connect(self.close)
        
        self.init_hardware_threads()
        self.connect_ui_signals()

        # Floating Gallery Button
        self.gallery_btn = QPushButton("🖼️", self.main_view)
        self.gallery_btn.setGeometry(20, 380, 60, 60) 
        self.gallery_btn.setStyleSheet("""
            QPushButton {
                background-color: #222222; 
                color: white; 
                font-size: 24px; 
                border-radius: 30px; 
                border: 2px solid #555555;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
        """)
        self.gallery_btn.clicked.connect(self.open_gallery)

    def init_hardware_threads(self):
        self.camera_thread = QThread(self)
        self.camera_worker = CameraWorker()
        self.camera_worker.moveToThread(self.camera_thread)
        self.camera_thread.started.connect(self.camera_worker.start_stream)
        
        self.camera_worker.frame_ready.connect(self.update_video_feed)
        self.camera_worker.high_res_saved_notification.connect(self.handle_capture_finished)
        self.request_high_res_capture.connect(self.camera_worker.capture_maximum_resolution_still)
        self.request_video_start.connect(self.camera_worker.start_video_recording)
        self.request_video_stop.connect(self.camera_worker.stop_video_recording)
        self.camera_thread.start()

        self.gpio_thread = QThread(self)
        self.gpio_worker = GPIOWorker()
        self.gpio_worker.moveToThread(self.gpio_thread)
        self.gpio_thread.started.connect(self.gpio_worker.monitor_pins)
        self.gpio_worker.rotated_clockwise.connect(self.main_view.navigate_menu_down)
        self.gpio_worker.rotated_counter_clockwise.connect(self.main_view.navigate_menu_up)
        self.gpio_worker.button_pressed.connect(self.handle_hardware_capture)
        self.gpio_thread.start()

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
                self.main_view.update_mode_text("Capturing 64MP... Please wait.")
                QApplication.processEvents() 
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"IMG_64MP_{timestamp}.jpg"
                filepath = os.path.join(self.output_folder, filename)
                self.request_high_res_capture.emit(filepath)
        
        elif media_type == "video":
            if not self.is_recording:
                self.is_recording = True
                self.recording_seconds = 0
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"VID_{timestamp}.avi"
                filepath = os.path.join(self.output_folder, filename)
                
                self.request_video_start.emit(filepath)
                
                self.main_view.timer_label.setText("REC 00:00:00")
                self.main_view.timer_label.show()
                self.main_view.video_btn.setStyleSheet("background-color: #990000; border-radius: 20px; border: 4px solid #FFFFFF;")
                self.recording_timer.start(1000)
            else:
                self.is_recording = False
                self.recording_timer.stop()
                
                self.request_video_stop.emit()
                
                self.main_view.timer_label.hide()
                self.main_view.video_btn.setStyleSheet("background-color: #FF0000; border-radius: 20px; border: 2px solid #FFFFFF;")
                print("[UI Action] Video recording mode toggled off.")

    @pyqtSlot(str)
    def handle_capture_finished(self, saved_path):
        self.main_view.update_mode_text(self.current_mode)
        print(f"[SUCCESS] High-fidelity 14MB capture saved safely to: {saved_path}")

    def update_recording_stopwatch(self):
        self.recording_seconds += 1
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

    def open_gallery(self):
        print("[UI] Searching for the latest capture...")
        
        # Search the captures folder for any files
        search_path = os.path.join(self.output_folder, "*")
        list_of_files = glob.glob(search_path)
        
        if list_of_files:
            # Find the file with the most recent modification timestamp
            latest_file = max(list_of_files, key=os.path.getmtime)
            print(f"[UI] Opening newest file: {latest_file}")
            
            # Open that specific file in the OS default viewer
            file_url = QUrl.fromLocalFile(latest_file)
            QDesktopServices.openUrl(file_url)
        else:
            # Fallback: If the folder is empty, just open the folder itself
            print("[UI] Folder is empty. Opening directory instead...")
            folder_url = QUrl.fromLocalFile(self.output_folder)
            QDesktopServices.openUrl(folder_url)

    def closeEvent(self, event):
        print("[SYSTEM] Initiating hardware worker shutdown sequence...")
        
        if self.is_recording:
            self.camera_worker.stop_video_recording()
            
        self.camera_worker.stop()
        self.gpio_worker.running = False
        self.sys_worker.running = False
        
        import os
        os.system("pkill -9 -f rpicam-vid")
        os.system("pkill -9 -f rpicam-jpeg")
        
        self.camera_thread.quit()
        self.gpio_thread.quit()
        self.sys_thread.quit()
        
        print("[SYSTEM] Core engine interface shutdown complete.")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RpiCameraApp()
    window.showMaximized() 
    sys.exit(app.exec())