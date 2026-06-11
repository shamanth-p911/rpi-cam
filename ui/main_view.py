from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QListWidget, QProgressBar)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class MainView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #000000; color: #FFFFFF;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ================= TOP BAR ELEMENT =================
        top_bar = QHBoxLayout()
        
        self.mode_icon_btn = QPushButton()
        self.mode_icon_btn.setFixedSize(65, 65)
        self.mode_icon_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B3C5D; 
                border: 3px solid #D9B310;
                border-radius: 5px;
            }
            QPushButton:pressed { background-color: #1D5F8A; }
        """)
        top_bar.addWidget(self.mode_icon_btn)

        self.mode_status_label = QLabel("specify current mode(manual/auto:topic)")
        self.mode_status_label.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        self.mode_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_bar.addWidget(self.mode_status_label, stretch=1)

        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(65, 65)
        self.settings_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; }")
        self.settings_btn.setText("⚙")
        self.settings_btn.setFont(QFont("Arial", 28))
        top_bar.addWidget(self.settings_btn)

        main_layout.addLayout(top_bar)

        # ================= CENTER STAGE VIEWPORT =================
        self.center_container = QWidget()
        self.center_layout = QHBoxLayout(self.center_container)
        self.center_layout.setContentsMargins(0, 10, 0, 10)

        # Container to stack the feed and the live recording duration timer
        feed_stack_layout = QVBoxLayout()
        
        self.timer_label = QLabel("REC 00:00:00")
        self.timer_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("color: #FF3333; background-color: rgba(0,0,0,150); padding: 5px; border-radius: 4px;")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.timer_label.hide() # Keep hidden until recording starts
        feed_stack_layout.addWidget(self.timer_label)

        self.feed_label = QLabel("camera live feed")
        self.feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_label.setFont(QFont("Arial", 14))
        self.feed_label.setStyleSheet("border: 2px solid #111111; background-color: #050505;")
        feed_stack_layout.addWidget(self.feed_label, stretch=1)
        
        self.center_layout.addLayout(feed_stack_layout, stretch=3)

        self.mode_menu = QListWidget()
        self.mode_menu.addItems(["-mqtt topic1", "-mqtt topic2", "-mqtt topic3", "-add topic", "-manual"])
        self.setup_dropdown_style(self.mode_menu)
        self.center_layout.addWidget(self.mode_menu, stretch=1)
        self.mode_menu.hide()

        self.settings_menu = QListWidget()
        self.settings_menu.addItems(["-exp", "-shutter speed", "-focus", "-zoom"])
        self.setup_dropdown_style(self.settings_menu)
        self.center_layout.addWidget(self.settings_menu, stretch=1)
        self.settings_menu.hide()

        main_layout.addWidget(self.center_container, stretch=1)

        # ================= BOTTOM METER & CONTROL CONTROLLERS =================
        bottom_bar = QHBoxLayout()

        battery_layout = QVBoxLayout()
        self.battery_label = QLabel("Battery: --%")
        self.battery_label.setFont(QFont("Arial", 11))
        self.battery_bar = QProgressBar()
        self.battery_bar.setFixedSize(130, 12)
        self.battery_bar.setStyleSheet("""
            QProgressBar { background-color: #222222; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #00CC66; }
        """)
        self.battery_bar.setTextVisible(False)
        battery_layout.addWidget(self.battery_label)
        battery_layout.addWidget(self.battery_bar)
        bottom_bar.addLayout(battery_layout)

        bottom_bar.addStretch(1)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(25)
        
        cam_block = QVBoxLayout()
        self.camera_btn = QPushButton()
        self.camera_btn.setFixedSize(55, 55)
        self.camera_btn.setStyleSheet("background-color: #E0E0E0; border-radius: 27px; border: 2px solid #FFFFFF;")
        cam_lbl = QLabel("Camera")
        cam_lbl.setFont(QFont("Arial", 11))
        cam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam_block.addWidget(self.camera_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        cam_block.addWidget(cam_lbl)
        controls_layout.addLayout(cam_block)

        video_block = QVBoxLayout()
        self.video_btn = QPushButton()
        self.video_btn.setFixedSize(40, 40)
        self.video_btn.setStyleSheet("background-color: #FF0000; border-radius: 20px; border: 2px solid #FFFFFF;")
        vid_lbl = QLabel("Video")
        vid_lbl.setFont(QFont("Arial", 11))
        vid_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_block.addWidget(self.video_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        video_block.addWidget(vid_lbl)
        controls_layout.addLayout(video_block)

        bottom_bar.addLayout(controls_layout)
        bottom_bar.addStretch(1)

        storage_layout = QVBoxLayout()
        self.storage_label = QLabel("SD Card: --% Full")
        self.storage_label.setFont(QFont("Arial", 11))
        self.storage_bar = QProgressBar()
        self.storage_bar.setFixedSize(160, 12)
        self.storage_bar.setStyleSheet("""
            QProgressBar { background-color: #222222; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #D4AF37; }
        """)
        self.storage_bar.setTextVisible(False)
        storage_layout.addWidget(self.storage_label)
        storage_layout.addWidget(self.storage_bar)
        bottom_bar.addLayout(storage_layout)

        main_layout.addLayout(bottom_bar)

        self.mode_icon_btn.clicked.connect(self.toggle_mode_menu)
        self.settings_btn.clicked.connect(self.toggle_settings_menu)

    def setup_dropdown_style(self, menu_widget):
        menu_widget.setStyleSheet("""
            QListWidget {
                background-color: #050505;
                color: #3399FF;
                border: 1px solid #222222;
                font-size: 16px;
                padding: 5px;
            }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #111111; color: #FFFFFF; font-weight: bold; }
        """)

    def toggle_mode_menu(self):
        self.settings_menu.hide()
        self.mode_menu.setVisible(not self.mode_menu.isVisible())

    def toggle_settings_menu(self):
        self.mode_menu.hide()
        self.settings_menu.setVisible(not self.settings_menu.isVisible())

    def update_mode_text(self, text):
        self.mode_status_label.setText(text)

    def update_system_status(self, battery_value, storage_value):
        self.battery_bar.setValue(int(battery_value))
        self.battery_label.setText(f"Battery: {int(battery_value)}%")
        
        self.storage_bar.setValue(int(storage_value))
        self.storage_label.setText(f"SD Card: {int(storage_value)}% Full")

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
