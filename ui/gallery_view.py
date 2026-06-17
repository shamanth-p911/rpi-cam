import os
import glob
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon

class GalleryView(QDialog):
    def __init__(self, capture_folder, parent=None):
        super().__init__(parent)
        self.capture_folder = capture_folder
        self.image_files = []
        self.current_index = 0
        
        self.setWindowTitle("Media Gallery")
        self.showFullScreen()
        self.setStyleSheet("background-color: #111111;") 
        
        self.image_label = QLabel("No images found.")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("color: #FFFFFF; font-size: 24px; border: none;")
        
        self.close_btn = QPushButton("✖")
        self.close_btn.setFixedSize(50, 50)
        self.close_btn.setStyleSheet("background-color: transparent; color: white; font-size: 24px; border: none; font-weight: bold;")
        self.close_btn.clicked.connect(self.close)
        
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        top_layout.addWidget(self.close_btn)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.image_label, 1) 
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)
        
        self.swipe_start_x = 0

    def load_images(self):
        search_path = os.path.join(self.capture_folder, "*.jpg")
        self.image_files = sorted(glob.glob(search_path), key=os.path.getmtime, reverse=True)
        
        if self.image_files:
            self.current_index = 0
            self.display_current_image()
        else:
            self.image_label.setText("No images found in captures folder.")

    def display_current_image(self):
        if not self.image_files:
            return
            
        filepath = self.image_files[self.current_index]
        pixmap = QPixmap(filepath)
        scaled_pixmap = pixmap.scaled(
            self.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def show_next(self):
        if self.image_files and self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.display_current_image()

    def show_prev(self):
        if self.image_files and self.current_index > 0:
            self.current_index -= 1
            self.display_current_image()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.swipe_start_x = event.position().x()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            swipe_end_x = event.position().x()
            delta_x = swipe_end_x - self.swipe_start_x
            
            swipe_threshold = 50 
            if delta_x > swipe_threshold:
                self.show_prev() 
            elif delta_x < -swipe_threshold:
                self.show_next()