from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout,
                             QPushButton, QListWidget, QProgressBar,
                             QGraphicsDropShadowEffect, QSlider, QFrame,
                             QGraphicsOpacityEffect, QGridLayout, QDialog,
                             QLineEdit, QCheckBox, QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation
from PyQt6.QtGui import QFont, QColor

class MqttSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Network Profile Settings")
        self.setFixedSize(400, 320) # Reduced height since fields were removed
        self.setStyleSheet("background-color: #1A1A1A; color: #FFFFFF; font-size: 14px;")
        
        self.delete_requested = False  
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.enabled_chk = QCheckBox("Enable MQTT Remote Access")
        self.broker_input = QLineEdit()
        self.port_input = QLineEdit()
        self.topic_input = QLineEdit()
        
        for widget in [self.name_input, self.broker_input, self.port_input, self.topic_input]:
            widget.setStyleSheet("background-color: #0D0D0D; border: 1px solid #333; padding: 5px; border-radius: 4px; color: #FFFFFF;")
        
        form_layout.addRow("Network Name:", self.name_input)
        form_layout.addRow(self.enabled_chk)
        form_layout.addRow("Broker IP/Host:", self.broker_input)
        form_layout.addRow("Port:", self.port_input)
        form_layout.addRow("Subscribe Topic:", self.topic_input)
        
        layout.addLayout(form_layout)
        
        self.delete_btn = QPushButton("🗑️ Delete Profile")
        self.delete_btn.setStyleSheet("""
            QPushButton { background-color: #551111; color: white; padding: 6px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #AA2222; }
        """)
        self.delete_btn.clicked.connect(self.handle_delete)
        self.delete_btn.hide()
        layout.addWidget(self.delete_btn)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.setStyleSheet("""
            QPushButton { background-color: #2A2A2A; padding: 6px 15px; border-radius: 4px; color: white; }
            QPushButton:hover { background-color: #444; }
        """)
        layout.addWidget(self.buttons)

    def load_config(self, config, is_editing=False):
        self.name_input.setText(config.get("network_name", ""))
        self.enabled_chk.setChecked(config.get("enabled", True))
        self.broker_input.setText(config.get("broker", ""))
        self.port_input.setText(str(config.get("port", 1883)))
        self.topic_input.setText(config.get("topic", "camera/commands"))
        
        if is_editing:
            self.delete_btn.show()
            self.original_name = config.get("network_name", "")

    def handle_delete(self):
        self.delete_requested = True
        self.accept()

    def get_config(self):
        return {
            "network_name": self.name_input.text().strip(),
            "enabled": self.enabled_chk.isChecked(),
            "broker": self.broker_input.text().strip(),
            "port": int(self.port_input.text().strip() or 1883),
            "topic": self.topic_input.text().strip(),
            "username": "", # Kept for backend compatibility
            "password": "", 
            "client_id": "rpicam_client" 
        }


class MainView(QWidget):
    zoom_changed = pyqtSignal(float)
    request_mqtt_save = pyqtSignal(dict) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_storage_free = 100.0
        self.mqtt_config = {"active_profile": "Manual", "profiles": []}
        self.init_ui()

    def set_initial_mqtt_config(self, config):
        self.mqtt_config = config
        self.rebuild_network_menu()
        
    def init_ui(self):
        self.setStyleSheet(
            "background-color: #050505; color: #FFFFFF;"
            "font-family: 'Segoe UI', Arial, sans-serif;"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0) 
        root.setSpacing(0)

        root.addLayout(self._build_top_bar())
        root.addWidget(self._build_hud_center(), stretch=1)

        self.mode_icon_btn.clicked.connect(self.toggle_mode_menu)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(40)
        self.zoom_slider.setValue(10)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        
        self.update_control_sizes("photo")

    def _build_top_bar(self):
        bar = QHBoxLayout()
        bar.setSpacing(10)
        bar.setContentsMargins(12, 0, 12, 10)

        self.mode_icon_btn = QPushButton("⌘  NETWORK")
        self.mode_icon_btn.setFixedHeight(32)
        self.mode_icon_btn.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.mode_icon_btn.setStyleSheet("""
            QPushButton {
                background-color: #111111; color: #888888;
                border: 1px solid #2A2A2A; border-radius: 16px;
                padding: 0 16px; letter-spacing: 1px;
            }
            QPushButton:pressed { background-color: #1A1A1A; color: #FFFFFF; }
        """)
        bar.addWidget(self.mode_icon_btn)

        self.mode_status_label = QLabel("MANUAL")
        self.mode_status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.mode_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_status_label.setStyleSheet("""
            background-color: #111111; color: #CCCCCC;
            border: 1px solid #2A2A2A; border-radius: 14px;
            padding: 4px 18px; letter-spacing: 2px;
        """)
        bar.addWidget(self.mode_status_label, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)

        self.mqtt_status_indicator = QLabel("●")
        self.mqtt_status_indicator.setFont(QFont("Arial", 14))
        self.mqtt_status_indicator.setStyleSheet("color: #555555; background: transparent;")
        self.mqtt_status_indicator.setToolTip("MQTT Offline")
        bar.addWidget(self.mqtt_status_indicator)
        return bar

    def update_mqtt_status(self, text, color):
        self.mqtt_status_indicator.setStyleSheet(f"color: {color}; background: transparent;")
        self.mqtt_status_indicator.setToolTip(f"MQTT Status: {text}")

    def _build_hud_center(self):
        self.hud_container = QWidget()
        self.hud_layout = QGridLayout(self.hud_container)
        self.hud_layout.setContentsMargins(0, 0, 0, 0)

        self.feed_label = QLabel("Initializing 12MP Sensor…")
        self.feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_label.setFont(QFont("Arial", 11))
        self.feed_label.setStyleSheet("background-color: #000000; color: #444444;")
        self.hud_layout.addWidget(self.feed_label, 0, 0)

        top_hud_container = QWidget()
        top_hud_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        top_hud_container.setStyleSheet("background: transparent;")
        top_hud = QHBoxLayout(top_hud_container)
        top_hud.setContentsMargins(20, 20, 20, 20)

        self.timer_label = QLabel("⏺  00:00:00")
        self.timer_label.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("""
            color: #FF2222; background-color: rgba(18, 0, 0, 210);
            border: 1px solid #FF2222; padding: 3px 12px; border-radius: 6px;
        """)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.hide()

        self.zoom_badge = QLabel("1.0×")
        self.zoom_badge.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.zoom_badge.setStyleSheet("""
            color: #26D0CE; background-color: rgba(0, 20, 20, 200);
            border: 1px solid #26D0CE; padding: 2px 10px; border-radius: 5px;
        """)
        self.zoom_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_badge.hide()

        top_hud.addStretch(1)
        top_hud.addWidget(self.timer_label)
        top_hud.addStretch(1)
        top_hud.addWidget(self.zoom_badge)

        self.hud_layout.addWidget(top_hud_container, 0, 0, Qt.AlignmentFlag.AlignTop)

        self.mode_menu = QListWidget()
        self._style_list(self.mode_menu)
        self._shadow(self.mode_menu)
        self.mode_menu.setFixedWidth(220)
        self.mode_menu.hide()
        
        mode_menu_wrapper = QWidget()
        mode_menu_wrapper.setStyleSheet("background: transparent;")
        mm_layout = QHBoxLayout(mode_menu_wrapper)
        mm_layout.setContentsMargins(0, 0, 20, 0)
        mm_layout.addWidget(self.mode_menu)
        self.hud_layout.addWidget(mode_menu_wrapper, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        bottom_hud_container = QWidget()
        bottom_hud_container.setStyleSheet("background: transparent;")
        bottom_hud_layout = QHBoxLayout(bottom_hud_container)
        bottom_hud_layout.setContentsMargins(15, 10, 15, 20) 

        self.gallery_btn = QPushButton("🖼️")
        self.gallery_btn.setFixedSize(50, 50) 
        self.gallery_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(20, 20, 20, 180); color: white; font-size: 20px; 
                border-radius: 25px; border: 2px solid rgba(100, 100, 100, 150);
            }
            QPushButton:pressed { background-color: rgba(60, 60, 60, 200); }
        """)
        bottom_hud_layout.addWidget(self.gallery_btn)
        bottom_hud_layout.addStretch(1)

        bottom_hud_layout.addWidget(self._telemetry_block("PWR", "battery", "#00b09b", "#96c93d"))
        bottom_hud_layout.addStretch(2)

        shutter_controls = QHBoxLayout()
        shutter_controls.setSpacing(12)
        shutter_controls.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.shutter_btn = QPushButton()
        self._shadow(self.shutter_btn)

        self.mode_switch_btn = QPushButton("TOGGLE MODE")
        self.mode_switch_btn.setFixedSize(110, 28)
        self.mode_switch_btn.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.mode_switch_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(10, 10, 10, 180); color: #DDDDDD;
                border: 1px solid rgba(80, 80, 80, 150); border-radius: 14px;
                letter-spacing: 1px;
            }
            QPushButton:pressed { background-color: rgba(40, 40, 40, 200); color: #FFFFFF; }
        """)

        shutter_controls.addWidget(self.shutter_btn)
        shutter_controls.addWidget(self.mode_switch_btn)

        bottom_hud_layout.addLayout(shutter_controls)
        bottom_hud_layout.addStretch(3)

        info_layout = QHBoxLayout()
        info_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.storage_info_label = QLabel("")
        self.storage_info_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.storage_info_label.setStyleSheet("""
            color: #EDDE5D; background-color: rgba(10, 10, 10, 200);
            padding: 4px 10px; border-radius: 14px; border: 1px solid rgba(80, 80, 80, 150);
        """)
        self.storage_info_label.hide()
        
        self.info_btn = QPushButton("ℹ️ INFO")
        self.info_btn.setFixedSize(80, 28)
        self.info_btn.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.info_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(10, 10, 10, 180); color: #DDDDDD;
                border: 1px solid rgba(80, 80, 80, 150); border-radius: 14px;
            }
            QPushButton:pressed { background-color: rgba(40, 40, 40, 200); color: #FFFFFF; }
        """)
        self.info_btn.clicked.connect(self.toggle_storage_info)

        info_layout.addWidget(self.storage_info_label)
        info_layout.addWidget(self.info_btn)
        
        bottom_hud_layout.addLayout(info_layout)
        self.hud_layout.addWidget(bottom_hud_container, 0, 0, Qt.AlignmentFlag.AlignBottom)
        return self.hud_container

    def adjust_camera_zoom(self, step):
        current_val = self.zoom_slider.value()
        new_val = max(self.zoom_slider.minimum(), min(self.zoom_slider.maximum(), current_val + step))
        self.zoom_slider.setValue(new_val)

    def rebuild_network_menu(self):
        self.mode_menu.clear()
        self.mode_menu.addItem("  Manual Control")
        for p in self.mqtt_config.get("profiles", []):
            self.mode_menu.addItem(f"  {p['network_name']}")
        self.mode_menu.addItem("  + Add Network")

    def open_mqtt_dialog(self, target_profile_name=None):
        dialog = MqttSettingsDialog(self)
        
        if target_profile_name:
            profile_data = next((p for p in self.mqtt_config.get("profiles", []) if p["network_name"] == target_profile_name), None)
            if profile_data:
                dialog.load_config(profile_data, is_editing=True)
        else:
            blank_config = {
                "network_name": "", "enabled": True, "broker": "", "port": 1883,
                "topic": "camera/commands", "username": "", "password": "", "client_id": ""
            }
            dialog.load_config(blank_config, is_editing=False)
            
        if dialog.exec():
            profiles = self.mqtt_config.get("profiles", [])
            
            if dialog.delete_requested and target_profile_name:
                profiles = [p for p in profiles if p["network_name"] != target_profile_name]
                self.mqtt_config["profiles"] = profiles
                self.mqtt_config["active_profile"] = "Manual"
            else:
                new_profile = dialog.get_config()
                if new_profile["network_name"]:
                    if target_profile_name:
                        profiles = [p for p in profiles if p["network_name"] != target_profile_name]
                    else:
                        profiles = [p for p in profiles if p["network_name"] != new_profile["network_name"]]
                        
                    profiles.append(new_profile)
                    self.mqtt_config["profiles"] = profiles
                    self.mqtt_config["active_profile"] = new_profile["network_name"]
            
            self.request_mqtt_save.emit(self.mqtt_config)
            self.rebuild_network_menu()

    def _telemetry_block(self, title, attr_prefix, c1, c2):
        container = QWidget()
        container.setStyleSheet("background-color: rgba(10, 10, 10, 180); border-radius: 8px; padding: 4px;")
        col = QVBoxLayout(container)
        col.setContentsMargins(6, 4, 6, 4)
        col.setSpacing(3)

        header = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #AAAAAA; letter-spacing: 1px; background: transparent;")

        pct_lbl = QLabel("0%")
        pct_lbl.setFont(QFont("Consolas", 8))
        pct_lbl.setStyleSheet("color: #EEEEEE; background: transparent;")
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        header.addWidget(lbl)
        header.addStretch()
        header.addWidget(pct_lbl)

        bar = QProgressBar()
        bar.setFixedSize(90, 6)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #222222; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c1}, stop:1 {c2});
                border-radius: 3px;
            }}
        """)

        col.addLayout(header)
        col.addWidget(bar)

        setattr(self, f"{attr_prefix}_bar", bar)
        setattr(self, f"{attr_prefix}_pct_label", pct_lbl)
        return container

    def _hline(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #333333; border: none;")
        return line

    def _shadow(self, widget):
        s = QGraphicsDropShadowEffect(self)
        s.setBlurRadius(14)
        s.setColor(QColor(0, 0, 0, 180))
        s.setOffset(0, 3)
        widget.setGraphicsEffect(s)

    def _style_list(self, lw):
        lw.setStyleSheet("""
            QListWidget {
                background-color: rgba(13, 13, 13, 220); color: #CCCCCC;
                border: 1px solid #333333; border-radius: 12px;
                font-size: 14px; padding: 4px;
            }
            QListWidget::item { padding: 11px 10px; border-bottom: 1px solid #222222; border-radius: 6px; margin: 2px; }
            QListWidget::item:hover { background-color: rgba(40, 40, 40, 150); }
            QListWidget::item:selected {
                background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1A2980, stop:1 #26D0CE);
                color: #FFFFFF; font-weight: bold;
            }
        """)

    def _on_zoom_changed(self, value):
        zoom = value / 10.0
        if zoom > 1.0:
            self.zoom_badge.setText(f"{zoom:.1f}×")
            self.zoom_badge.show()
        else:
            self.zoom_badge.hide()
        self.zoom_changed.emit(zoom)

    def toggle_mode_menu(self):
        self.mode_menu.setVisible(not self.mode_menu.isVisible())

    def update_mode_text(self, text):
        self.mode_status_label.setText(text.upper())

    def update_system_status(self, battery_value, storage_value):
        if hasattr(self, 'battery_bar'):
            self.battery_bar.setValue(int(battery_value))
            self.battery_pct_label.setText(f"{int(battery_value)}%")
        
        self.current_storage_free = 100.0 - float(storage_value)
        if self.storage_info_label.isVisible():
            self.storage_info_label.setText(f"{self.current_storage_free:.1f}% FREE")

    def toggle_storage_info(self):
        if self.storage_info_label.isVisible():
            self.storage_info_label.hide()
            self.info_btn.setStyleSheet("""
                QPushButton { background-color: rgba(10, 10, 10, 180); color: #DDDDDD; border: 1px solid rgba(80, 80, 80, 150); border-radius: 14px; }
                QPushButton:pressed { background-color: rgba(40, 40, 40, 200); color: #FFFFFF; }
            """)
        else:
            self.storage_info_label.setText(f"{self.current_storage_free:.1f}% FREE")
            self.storage_info_label.show()
            self.info_btn.setStyleSheet("""
                QPushButton { background-color: rgba(60, 60, 60, 200); color: #FFFFFF; border: 1px solid #777777; border-radius: 14px; }
            """)

    def update_control_sizes(self, active_mode):
        if active_mode == "photo":
            self.shutter_btn.setFixedSize(54, 54)
            self.shutter_btn.setStyleSheet("background-color: #F0F0F0; border-radius: 27px; border: 4px solid #2A2A2A;")
        elif active_mode == "video":
            self.shutter_btn.setFixedSize(54, 54)
            self.shutter_btn.setStyleSheet("background-color: #EE0022; border-radius: 27px; border: 4px solid #FFFFFF;")

    def trigger_flash(self):
        self.flash_overlay = QWidget(self.feed_label)
        self.flash_overlay.setStyleSheet("background-color: #FFFFFF; border-radius: 10px;")
        self.flash_overlay.setGeometry(self.feed_label.rect())
        self.flash_overlay.show()

        self.opacity_effect = QGraphicsOpacityEffect(self.flash_overlay)
        self.flash_overlay.setGraphicsEffect(self.opacity_effect)

        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(350)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        
        self.fade_anim.finished.connect(self.flash_overlay.deleteLater)
        self.fade_anim.start()