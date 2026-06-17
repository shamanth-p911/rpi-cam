from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout,
                             QPushButton, QListWidget, QProgressBar,
                             QGraphicsDropShadowEffect, QSlider, QFrame,
                             QGraphicsOpacityEffect, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation
from PyQt6.QtGui import QFont, QColor

class MainView(QWidget):
    zoom_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_storage_free = 100.0
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(
            "background-color: #050505; color: #FFFFFF;"
            "font-family: 'Segoe UI', Arial, sans-serif;"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0) # Removed bottom margin so feed hits the bottom edge
        root.setSpacing(0)

        # 1. Top Bar (Remains anchored at the top)
        root.addLayout(self._build_top_bar())
        
        # 2. The HUD Layout (Camera Feed + Overlapping Controls)
        root.addWidget(self._build_hud_center(), stretch=1)

        self.mode_icon_btn.clicked.connect(self.toggle_mode_menu)
        self.settings_btn.clicked.connect(self.toggle_settings_menu)
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

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(32, 32)
        self.settings_btn.setFont(QFont("Arial", 16))
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #111111; border: 1px solid #2A2A2A;
                color: #666666; border-radius: 16px;
            }
            QPushButton:pressed { color: #FFFFFF; background-color: #1A1A1A; }
        """)
        bar.addWidget(self.settings_btn)
        return bar

    def _build_hud_center(self):
        """Creates a Grid Layout where all elements overlap on row 0, col 0"""
        self.hud_container = QWidget()
        self.hud_layout = QGridLayout(self.hud_container)
        self.hud_layout.setContentsMargins(0, 0, 0, 0)

        # ==========================================
        # LAYER 0: The Camera Feed (Background)
        # ==========================================
        self.feed_label = QLabel("Initializing 12MP Sensor…")
        self.feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_label.setFont(QFont("Arial", 11))
        # Feed gets no alignment flag, forcing it to stretch and fill the entire area
        self.feed_label.setStyleSheet("background-color: #000000; color: #444444;")
        self.hud_layout.addWidget(self.feed_label, 0, 0)

        # ==========================================
        # LAYER 1: Top Indicators (Timer & Zoom)
        # ==========================================
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

        # ==========================================
        # LAYER 2: Floating Menus (Right Aligned)
        # ==========================================
        self.mode_menu = QListWidget()
        self.mode_menu.addItems(["  MQTT Auto 1", "  MQTT Auto 2", "  MQTT Auto 3", "  + Add Network", "  Manual Control"])
        self._style_list(self.mode_menu)
        self._shadow(self.mode_menu)
        self.mode_menu.setFixedWidth(220)
        self.mode_menu.hide()
        
        # Add right-margin via a container
        mode_menu_wrapper = QWidget()
        mode_menu_wrapper.setStyleSheet("background: transparent;")
        mm_layout = QHBoxLayout(mode_menu_wrapper)
        mm_layout.setContentsMargins(0, 0, 20, 0)
        mm_layout.addWidget(self.mode_menu)
        self.hud_layout.addWidget(mode_menu_wrapper, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.settings_panel = self._build_settings_panel()
        self._shadow(self.settings_panel)
        self.settings_panel.setFixedWidth(300)
        self.settings_panel.hide()
        
        sp_wrapper = QWidget()
        sp_wrapper.setStyleSheet("background: transparent;")
        sp_layout = QHBoxLayout(sp_wrapper)
        sp_layout.setContentsMargins(0, 0, 20, 0)
        sp_layout.addWidget(self.settings_panel)
        self.hud_layout.addWidget(sp_wrapper, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # ==========================================
        # LAYER 3: Bottom Controls
        # ==========================================
        bottom_hud_container = QWidget()
        bottom_hud_container.setStyleSheet("background: transparent;")
        bottom_hud_layout = QHBoxLayout(bottom_hud_container)
        bottom_hud_layout.setContentsMargins(15, 10, 15, 20) # Floating margin above screen bottom

        # Gallery Button
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

        # Telemetry Block
        bottom_hud_layout.addWidget(self._telemetry_block("PWR", "battery", "#00b09b", "#96c93d"))
        bottom_hud_layout.addStretch(2)

        # Shutter Controls
        shutter_controls = QHBoxLayout()
        shutter_controls.setSpacing(12)
        shutter_controls.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.camera_btn = QPushButton()
        self._shadow(self.camera_btn)

        self.mode_switch_btn = QPushButton("PHOTO ⟷ VIDEO")
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

        self.video_btn = QPushButton()
        self._shadow(self.video_btn)

        shutter_controls.addWidget(self.camera_btn)
        shutter_controls.addWidget(self.mode_switch_btn)
        shutter_controls.addWidget(self.video_btn)

        bottom_hud_layout.addLayout(shutter_controls)
        bottom_hud_layout.addStretch(3)

        # Info Button 
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

    def _build_settings_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame { background-color: rgba(13, 13, 13, 220); border: 1px solid #333; border-radius: 12px; }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        title = QLabel("SETTINGS")
        title.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #888888; letter-spacing: 3px; border: none; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(self._hline())

        hdr = QHBoxLayout()
        icon_lbl = QLabel("⊕")
        icon_lbl.setStyleSheet("color: #26D0CE; font-size: 15px; border: none; background: transparent;")
        section_lbl = QLabel("ZOOM")
        section_lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        section_lbl.setStyleSheet("color: #AAAAAA; letter-spacing: 2px; border: none; background: transparent;")
        hdr.addWidget(icon_lbl)
        hdr.addWidget(section_lbl)
        hdr.addStretch()

        self.zoom_value_label = QLabel("1.0×")
        self.zoom_value_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.zoom_value_label.setStyleSheet("color: #26D0CE; border: none; background: transparent;")
        hdr.addWidget(self.zoom_value_label)
        layout.addLayout(hdr)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(40)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setFixedHeight(36)
        self.zoom_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #333333; border-radius: 2px; }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1A2980, stop:1 #26D0CE);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF; border: 2px solid #26D0CE;
                width: 18px; height: 18px; margin: -8px 0; border-radius: 9px;
            }
            QSlider::handle:horizontal:pressed { background: #26D0CE; }
        """)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        layout.addWidget(self.zoom_slider)

        foot = QHBoxLayout()
        lbl1x = QLabel("1×")
        lbl1x.setStyleSheet("color: #888888; font-size: 10px; border: none; background: transparent;")
        lbl4x = QLabel("4×")
        lbl4x.setStyleSheet("color: #888888; font-size: 10px; border: none; background: transparent;")

        reset_btn = QPushButton("Reset")
        reset_btn.setFixedHeight(24)
        reset_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #AAAAAA; border: 1px solid #444444; border-radius: 5px; font-size: 10px; padding: 0 10px; }
            QPushButton:pressed { color: #FFFFFF; border-color: #777777; }
        """)
        reset_btn.clicked.connect(lambda: self.zoom_slider.setValue(10))
        foot.addWidget(lbl1x)
        foot.addStretch()
        foot.addWidget(reset_btn)
        foot.addStretch()
        foot.addWidget(lbl4x)
        layout.addLayout(foot)
        layout.addWidget(self._hline())

        for row_label in ["Exposure", "Shutter Speed", "Focus Peaking"]:
            row = QHBoxLayout()
            lbl = QLabel(row_label)
            lbl.setFont(QFont("Arial", 10))
            lbl.setStyleSheet("color: #DDDDDD; border: none; background: transparent;")
            soon = QLabel("soon")
            soon.setFont(QFont("Arial", 9))
            soon.setStyleSheet("color: #777777; border: 1px solid #555555; border-radius: 4px; padding: 1px 6px; background: transparent;")
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(soon)
            layout.addLayout(row)

        layout.addStretch()
        return panel

    def _telemetry_block(self, title, attr_prefix, c1, c2):
        # Wrapped in a semi-transparent background so it's readable against the video
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
        self.zoom_value_label.setText(f"{zoom:.1f}×")
        if zoom > 1.0:
            self.zoom_badge.setText(f"{zoom:.1f}×")
            self.zoom_badge.show()
        else:
            self.zoom_badge.hide()
        self.zoom_changed.emit(zoom)

    def toggle_mode_menu(self):
        self.settings_panel.hide()
        self.mode_menu.setVisible(not self.mode_menu.isVisible())

    def toggle_settings_menu(self):
        self.mode_menu.hide()
        self.settings_panel.setVisible(not self.settings_panel.isVisible())

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
            self.camera_btn.setFixedSize(54, 54)
            self.camera_btn.setStyleSheet("background-color: #F0F0F0; border-radius: 27px; border: 4px solid #2A2A2A;")
            
            self.video_btn.setFixedSize(28, 28)
            self.video_btn.setStyleSheet("background-color: #3A0000; border-radius: 14px; border: 2px solid #1A1A1A;")
        elif active_mode == "video":
            self.camera_btn.setFixedSize(28, 28)
            self.camera_btn.setStyleSheet("background-color: #2A2A2A; border-radius: 14px; border: 2px solid #111111;")
            
            self.video_btn.setFixedSize(54, 54)
            self.video_btn.setStyleSheet("background-color: #EE0022; border-radius: 27px; border: 4px solid #FFFFFF;")

    def navigate_menu_up(self):
        if self.mode_menu.isVisible():
            r = self.mode_menu.currentRow()
            self.mode_menu.setCurrentRow(max(0, r - 1))

    def navigate_menu_down(self):
        if self.mode_menu.isVisible():
            r = self.mode_menu.currentRow()
            self.mode_menu.setCurrentRow(min(self.mode_menu.count() - 1, r + 1))

    def get_active_menu(self):
        if self.mode_menu.isVisible():
            return self.mode_menu
        return None

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