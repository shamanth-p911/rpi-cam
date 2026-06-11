from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QListWidget, QProgressBar, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class MainView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Deep OLED Black Background
        self.setStyleSheet("background-color: #030303; color: #FFFFFF; font-family: 'Segoe UI', Arial, sans-serif;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ================= TOP BAR (Cinematic Header) =================
        top_bar = QHBoxLayout()
        
        self.mode_icon_btn = QPushButton()
        self.mode_icon_btn.setFixedSize(60, 60)
        self.mode_icon_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1A2980, stop:1 #26D0CE); 
                border: 2px solid #333333;
                border-radius: 30px; 
            }
            QPushButton:pressed { opacity: 0.8; }
        """)
        self.apply_shadow(self.mode_icon_btn)
        top_bar.addWidget(self.mode_icon_btn)

        # Pill-shaped Status Badge
        self.mode_status_label = QLabel(" MANUAL MODE ")
        self.mode_status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.mode_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_status_label.setStyleSheet("""
            background-color: #111111; 
            color: #E0E0E0; 
            border: 1px solid #333333; 
            border-radius: 15px;
            padding: 5px 15px;
            letter-spacing: 2px;
        """)
        top_bar.addWidget(self.mode_status_label, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(60, 60)
        self.settings_btn.setStyleSheet("""
            QPushButton { background-color: #111111; border: 1px solid #333333; color: #AAAAAA; border-radius: 30px; }
            QPushButton:hover { color: #FFFFFF; background-color: #222222; }
        """)
        self.settings_btn.setFont(QFont("Arial", 24))
        self.apply_shadow(self.settings_btn)
        top_bar.addWidget(self.settings_btn)

        main_layout.addLayout(top_bar)

        # ================= CENTER STAGE (Viewfinder) =================
        self.center_container = QWidget()
        self.center_layout = QHBoxLayout(self.center_container)
        self.center_layout.setContentsMargins(0, 15, 0, 15)

        feed_stack_layout = QVBoxLayout()
        
        # Floating Cyber-Red Timer
        self.timer_label = QLabel(" REC 00:00:00 ")
        self.timer_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("""
            color: #FF1A1A; 
            background-color: rgba(20, 0, 0, 200); 
            border: 1px solid #FF1A1A;
            padding: 5px 15px; 
            border-radius: 8px;
        """)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.hide() 
        feed_stack_layout.addWidget(self.timer_label, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.feed_label = QLabel("Initializing 64MP Sensor...")
        self.feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_label.setFont(QFont("Arial", 12))
        # Sleek Viewfinder Border
        self.feed_label.setStyleSheet("""
            border: 2px solid #1A1A1A; 
            background-color: #0A0A0A; 
            border-radius: 12px;
        """)
        feed_stack_layout.addWidget(self.feed_label, stretch=1)
        
        self.center_layout.addLayout(feed_stack_layout, stretch=3)

        # Premium Floating Menus
        self.mode_menu = QListWidget()
        self.mode_menu.addItems(["  MQTT Auto 1", "  MQTT Auto 2", "  MQTT Auto 3", "  + Add Network", "  Manual Control"])
        self.setup_dropdown_style(self.mode_menu)
        self.apply_shadow(self.mode_menu)
        self.center_layout.addWidget(self.mode_menu, stretch=1)
        self.mode_menu.hide()

        self.settings_menu = QListWidget()
        self.settings_menu.addItems(["  Exposure", "  Shutter Speed", "  Focus Peaking", "  Digital Zoom"])
        self.setup_dropdown_style(self.settings_menu)
        self.apply_shadow(self.settings_menu)
        self.center_layout.addWidget(self.settings_menu, stretch=1)
        self.settings_menu.hide()

        main_layout.addWidget(self.center_container, stretch=1)

        # ================= BOTTOM DASHBOARD (HUD) =================
        bottom_bar = QHBoxLayout()

        # Telemetry: Battery (Neon Green Gradient)
        battery_layout = QVBoxLayout()
        self.battery_label = QLabel("PWR")
        self.battery_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.battery_label.setStyleSheet("color: #666666; letter-spacing: 1px;")
        self.battery_bar = QProgressBar()
        self.battery_bar.setFixedSize(120, 10)
        self.battery_bar.setStyleSheet("""
            QProgressBar { background-color: #111111; border: 1px solid #222; border-radius: 5px; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00b09b, stop:1 #96c93d); border-radius: 4px; }
        """)
        self.battery_bar.setTextVisible(False)
        battery_layout.addWidget(self.battery_label)
        battery_layout.addWidget(self.battery_bar)
        bottom_bar.addLayout(battery_layout)

        bottom_bar.addStretch(1)

        # Controls: The Aesthetic Switch Hub
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(25)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.camera_btn = QPushButton()
        self.apply_shadow(self.camera_btn)
        
        self.mode_switch_btn = QPushButton("⟷")
        self.mode_switch_btn.setFixedSize(60, 36)
        self.mode_switch_btn.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.mode_switch_btn.setStyleSheet("""
            QPushButton { background-color: #151515; color: #666666; border: 1px solid #333; border-radius: 18px; }
            QPushButton:pressed { background-color: #333333; color: #FFFFFF; }
        """)

        self.video_btn = QPushButton()
        self.apply_shadow(self.video_btn)

        controls_layout.addWidget(self.camera_btn)
        controls_layout.addWidget(self.mode_switch_btn)
        controls_layout.addWidget(self.video_btn)

        bottom_bar.addLayout(controls_layout)
        bottom_bar.addStretch(1)

        # Telemetry: Storage (Neon Gold Gradient)
        storage_layout = QVBoxLayout()
        self.storage_label = QLabel("MEM")
        self.storage_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.storage_label.setStyleSheet("color: #666666; letter-spacing: 1px;")
        self.storage_bar = QProgressBar()
        self.storage_bar.setFixedSize(120, 10)
        self.storage_bar.setStyleSheet("""
            QProgressBar { background-color: #111111; border: 1px solid #222; border-radius: 5px; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F09819, stop:1 #EDDE5D); border-radius: 4px; }
        """)
        self.storage_bar.setTextVisible(False)
        storage_layout.addWidget(self.storage_label)
        storage_layout.addWidget(self.storage_bar)
        bottom_bar.addLayout(storage_layout)

        main_layout.addLayout(bottom_bar)

        self.mode_icon_btn.clicked.connect(self.toggle_mode_menu)
        self.settings_btn.clicked.connect(self.toggle_settings_menu)
        
        self.update_control_sizes(active_mode="photo")

    def apply_shadow(self, widget):
        """Adds a subtle, premium drop shadow to UI elements to make them float."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 4)
        widget.setGraphicsEffect(shadow)

    def setup_dropdown_style(self, menu_widget):
        menu_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(15, 15, 15, 240);
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 12px;
                font-size: 15px;
                padding: 5px;
            }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #1A1A1A; border-radius: 6px; margin: 2px; }
            QListWidget::item:hover { background-color: #222222; }
            QListWidget::item:selected { 
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1A2980, stop:1 #26D0CE); 
                color: #FFFFFF; 
                font-weight: bold; 
            }
        """)

    def update_control_sizes(self, active_mode):
        if active_mode == "photo":
            self.camera_btn.setFixedSize(80, 80)
            self.camera_btn.setStyleSheet("background-color: #FFFFFF; border-radius: 40px; border: 6px solid #333333;")
            self.video_btn.setFixedSize(36, 36)
            self.video_btn.setStyleSheet("background-color: #4A0000; border-radius: 18px; border: 2px solid #111111;")
        elif active_mode == "video":
            self.camera_btn.setFixedSize(36, 36)
            self.camera_btn.setStyleSheet("background-color: #444444; border-radius: 18px; border: 2px solid #111111;")
            self.video_btn.setFixedSize(80, 80)
            self.video_btn.setStyleSheet("background-color: #FF0033; border-radius: 40px; border: 6px solid #FFFFFF;")

    def toggle_mode_menu(self):
        self.settings_menu.hide()
        self.mode_menu.setVisible(not self.mode_menu.isVisible())

    def toggle_settings_menu(self):
        self.mode_menu.hide()
        self.settings_menu.setVisible(not self.settings_menu.isVisible())

    def update_mode_text(self, text):
        self.mode_status_label.setText(f" {text.upper()} ")

    def update_system_status(self, battery_value, storage_value):
        self.battery_bar.setValue(int(battery_value))
        self.storage_bar.setValue(int(storage_value))

    def navigate_menu_up(self):
        active = self.get_active_menu()
        if active:
            curr = active.currentRow()
            active.setCurrentRow(max(0, curr - 1))

    def navigate_menu_down(self):
        active = self.get_active_menu()
        if active:
            curr = active.currentRow()
            active.setCurrentRow(min(active.count() - 1, curr + 1))

    def get_active_menu(self):
        if self.mode_menu.isVisible(): return self.mode_menu
        if self.settings_menu.isVisible(): return self.settings_menu
        return None