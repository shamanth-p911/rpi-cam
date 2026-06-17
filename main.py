import sys
import os
import time
import cv2
import glob
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt6.QtCore import QThread, pyqtSlot, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QShortcut, QKeySequence

from ui.main_view import MainView
from hardware.camera_worker import CameraWorker
from hardware.gpio_worker import GPIOWorker
from hardware.system_monitor import SystemMonitorWorker
from hardware.mqtt_worker import MQTTWorker
from ui.gallery_view import GalleryView

print("[SYSTEM] Booting up Arducam Dashboard...")

class RpiCameraApp(QMainWindow):
    request_high_res_capture = pyqtSignal(str)
    request_video_start = pyqtSignal(str)
    request_video_stop = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RPi Camera Module 3 Dashboard")
        self.setMinimumSize(800, 480) 
        
        self.output_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            print(f"[SYSTEM] Created storage folder layout at: {self.output_folder}")
            
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mqtt_config.json")
        
        self.latest_raw_frame = None
        self.is_recording = False
        self.recording_seconds = 0
        
        self.active_hardware_mode = "photo" 
        
        self.main_view = MainView(self)
        self.setCentralWidget(self.main_view)
        
        # Load profile configuration safely
        loaded_config = self.load_mqtt_config()
        self.current_mode = loaded_config.get("active_profile", "Manual")
        
        if self.current_mode != "Manual":
            self.main_view.update_mode_text(f"Auto: {self.current_mode}")
        else:
            self.main_view.update_mode_text("Manual")
        
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.update_recording_stopwatch)
        
        self.quit_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.quit_shortcut.activated.connect(self.close)
        
        self.init_hardware_threads()
        self.connect_ui_signals()
        
        # Apply current active workspace configurations directly to thread logic
        self.apply_active_profile_to_worker(loaded_config)

    def load_mqtt_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    # Migration Strategy from old single-profile format
                    if "broker" in data:
                        migrated = {
                            "active_profile": "DefaultProfile" if data.get("enabled") else "Manual",
                            "profiles": [
                                {
                                    "network_name": "DefaultProfile",
                                    "enabled": data.get("enabled", False),
                                    "broker": data.get("broker", ""),
                                    "port": data.get("port", 1883),
                                    "topic": data.get("topic", "camera/commands"),
                                    "username": data.get("username", ""),
                                    "password": data.get("password", ""),
                                    "client_id": data.get("client_id", "rpicam_client")
                                }
                            ]
                        }
                        return migrated
                    return data
            except Exception as e:
                print(f"[MQTT] Failed to load config: {e}")
        return {"active_profile": "Manual", "profiles": []}

    def save_mqtt_config(self, config_dict):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_dict, f, indent=4)
            self.apply_active_profile_to_worker(config_dict)
            
            # Ensure the top-bar UI mode descriptive label displays the right configuration
            self.current_mode = config_dict.get("active_profile", "Manual")
            if self.current_mode != "Manual":
                self.main_view.update_mode_text(f"Auto: {self.current_mode}")
            else:
                self.main_view.update_mode_text("Manual")
        except Exception as e:
            print(f"[MQTT] Failed to save config: {e}")

    def apply_active_profile_to_worker(self, config):
        active = config.get("active_profile", "Manual")
        if active == "Manual":
            disabled_cfg = {"enabled": False}
            if hasattr(self, 'mqtt_worker'):
                self.mqtt_worker.apply_config(disabled_cfg)
        else:
            for p in config.get("profiles", []):
                if p["network_name"] == active:
                    if hasattr(self, 'mqtt_worker'):
                        self.mqtt_worker.apply_config(p)
                    break

    def init_hardware_threads(self):
        # --- Camera ---
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

        # --- GPIO ---
        self.gpio_thread = QThread(self)
        self.gpio_worker = GPIOWorker()
        self.gpio_worker.moveToThread(self.gpio_thread)
        self.gpio_thread.started.connect(self.gpio_worker.monitor_pins)
        self.gpio_worker.rotated_clockwise.connect(self.main_view.navigate_menu_down)
        self.gpio_worker.rotated_counter_clockwise.connect(self.main_view.navigate_menu_up)
        self.gpio_worker.button_pressed.connect(self.handle_hardware_capture)
        self.gpio_thread.start()

        # --- System Monitor ---
        self.sys_thread = QThread(self)
        self.sys_worker = SystemMonitorWorker()
        self.sys_worker.moveToThread(self.sys_thread)
        self.sys_thread.started.connect(self.sys_worker.start_monitoring)
        self.sys_worker.status_updated.connect(self.main_view.update_system_status)
        self.sys_thread.start()
        
        # --- MQTT Worker ---
        self.mqtt_thread = QThread(self)
        self.mqtt_worker = MQTTWorker()
        self.mqtt_worker.moveToThread(self.mqtt_thread)
        self.mqtt_thread.started.connect(self.mqtt_worker.run_loop)
        
        self.mqtt_worker.photo_requested.connect(self.handle_mqtt_photo)
        self.mqtt_worker.video_start_requested.connect(self.handle_mqtt_video_start)
        self.mqtt_worker.video_stop_requested.connect(self.handle_mqtt_video_stop)
        self.mqtt_worker.mqtt_connected.connect(lambda: self.main_view.update_mqtt_status("Connected", "#00FF00"))
        self.mqtt_worker.mqtt_disconnected.connect(lambda: self.main_view.update_mqtt_status("Disconnected", "#FF0000"))
        self.mqtt_worker.mqtt_error.connect(lambda e: self.main_view.update_mqtt_status(f"Error", "#FFA500"))
        
        self.mqtt_thread.start()

    def connect_ui_signals(self):
        self.main_view.camera_btn.clicked.connect(lambda: self.capture_media("photo"))
        self.main_view.video_btn.clicked.connect(lambda: self.capture_media("video"))
        self.main_view.mode_switch_btn.clicked.connect(self.toggle_hardware_mode)
        self.main_view.mode_menu.itemClicked.connect(self.handle_mode_change)
        self.main_view.zoom_changed.connect(self.camera_worker.set_zoom)
        self.main_view.gallery_btn.clicked.connect(self.open_gallery)
        
        self.main_view.request_mqtt_save.connect(self.save_mqtt_config)
        self.main_view.set_initial_mqtt_config(self.load_mqtt_config())

    @pyqtSlot()
    def handle_mqtt_photo(self):
        print("[MQTT] Photo command received. Executing capture.")
        self.capture_media("photo")

    @pyqtSlot()
    def handle_mqtt_video_start(self):
        if not self.is_recording:
            print("[MQTT] Video start command received. Executing record.")
            self.capture_media("video")
        else:
            print("[MQTT] Video start ignored (already recording).")

    @pyqtSlot()
    def handle_mqtt_video_stop(self):
        if self.is_recording:
            print("[MQTT] Video stop command received. Stopping record.")
            self.capture_media("video")
        else:
            print("[MQTT] Video stop ignored (not recording).")

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

    def toggle_hardware_mode(self):
        if self.active_hardware_mode == "photo":
            self.active_hardware_mode = "video"
            print("[UI] Hardware button armed for VIDEO recording.")
        else:
            self.active_hardware_mode = "photo"
            print("[UI] Hardware button armed for PHOTO capture.")
        self.main_view.update_control_sizes(self.active_hardware_mode)

    def handle_hardware_capture(self):
        self.capture_media(self.active_hardware_mode)

    def capture_media(self, media_type):
        if media_type == "photo":
            if self.latest_raw_frame is not None:
                self.main_view.trigger_flash()
                self.main_view.update_mode_text("Capturing 12MP... Please wait.")
                QApplication.processEvents() 
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"IMG_12MP_{timestamp}.jpg"
                filepath = os.path.join(self.output_folder, filename)
                self.request_high_res_capture.emit(filepath)
        
        elif media_type == "video":
            if not self.is_recording:
                self.is_recording = True
                self.recording_seconds = 0
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"VID_{timestamp}.mp4"
                filepath = os.path.join(self.output_folder, filename)
                
                self.request_video_start.emit(filepath)
                
                self.main_view.timer_label.setText("REC 00:00:00")
                self.main_view.timer_label.show()
                self.main_view.video_btn.setStyleSheet(
                    "background-color: #FF0000; border-radius: 27px; border: 4px solid #FFFFFF;"
                )
                self.recording_timer.start(1000)
            else:
                self.is_recording = False
                self.recording_timer.stop()
                self.request_video_stop.emit()
                self.main_view.timer_label.hide()
                self.main_view.update_control_sizes(self.active_hardware_mode)
                print("[UI Action] Video recording stopped.")

    @pyqtSlot(str)
    def handle_capture_finished(self, saved_path):
        if self.current_mode != "Manual":
            self.main_view.update_mode_text(f"Auto: {self.current_mode}")
        else:
            self.main_view.update_mode_text("Manual")
        print(f"[SUCCESS] High-fidelity capture saved safely to: {saved_path}")

    def update_recording_stopwatch(self):
        self.recording_seconds += 1
        hours = self.recording_seconds // 3600
        minutes = (self.recording_seconds % 3600) // 60
        seconds = self.recording_seconds % 60
        self.main_view.timer_label.setText(f"REC {hours:02d}:{minutes:02d}:{seconds:02d}")

    def handle_mode_change(self, item):
        selection = item.text().strip()
        
        if "+ add network" in selection.lower():
            self.main_view.mode_menu.hide()
            self.main_view.open_mqtt_dialog()
            return
            
        if "manual control" in selection.lower():
            self.current_mode = "Manual"
            self.main_view.update_mode_text("Manual")
            config = self.main_view.mqtt_config
            config["active_profile"] = "Manual"
            self.save_mqtt_config(config)
            self.main_view.mode_menu.hide()
        else:
            # When an existing profile topic entry is clicked, trigger the layout dialog box loaded with its parameters
            self.main_view.mode_menu.hide()
            self.main_view.open_mqtt_dialog(target_profile_name=selection)

    def open_gallery(self):
        print("[UI] Opening gallery...")
        gallery = GalleryView(self.output_folder, parent=self)
        gallery.load_images()
        gallery.exec()

    def closeEvent(self, event):
        print("[SYSTEM] Initiating hardware worker shutdown sequence...")
        if self.is_recording:
            self.camera_worker.stop_video_recording()
        
        self.camera_worker.stop()
        self.gpio_worker.running = False
        self.sys_worker.running = False
        self.mqtt_worker.stop()
        
        os.system("pkill -9 -f rpicam-vid")
        os.system("pkill -9 -f rpicam-jpeg")
        
        self.camera_thread.quit()
        self.gpio_thread.quit()
        self.sys_thread.quit()
        self.mqtt_thread.quit()
        print("[SYSTEM] Core engine interface shutdown complete.")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RpiCameraApp()
    window.showMaximized() 
    sys.exit(app.exec())