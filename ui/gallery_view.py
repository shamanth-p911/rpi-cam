import os
import glob
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QWidget
from PyQt6.QtCore import Qt, QThreadPool, QRunnable, pyqtSlot, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QPixmap, QFont

class CacheWorkerSignals(QObject):
    result_ready = pyqtSignal(str, QPixmap)

class CacheRunnable(QRunnable):
    """Decodes and scales raw disk files asynchronously to match viewport aspect ratios."""
    def __init__(self, filepath, target_size):
        super().__init__()
        self.filepath = filepath
        self.target_size = target_size
        self.signals = CacheWorkerSignals()

    def run(self):
        pixmap = QPixmap(self.filepath)
        if not pixmap.isNull():
            # Force absolute proportional downsizing without clipping logic boundaries
            scaled = pixmap.scaled(
                self.target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.signals.result_ready.emit(self.filepath, scaled)

class GalleryView(QDialog):
    def __init__(self, capture_folder, parent=None):
        super().__init__(parent)
        self.capture_folder = capture_folder
        self.media_files = []
        
        self.global_index = 0  
        self.page_size = 4
        self.is_fullscreen_active = False
        
        # Centralized image cache map
        self.pixmap_cache = {}
        self.thread_pool = QThreadPool.globalInstance()
        # Restrict concurrent tasks to keep Raspberry Pi core UI cycles completely unthrottled
        self.thread_pool.setMaxThreadCount(2)

        self.setWindowTitle("Media Grid Gallery")
        self.showFullScreen()
        self.setStyleSheet("background-color: #050505; border: none;") 
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        # --- Top Action Bar ---
        self.top_bar = QWidget()
        self.top_bar.setStyleSheet("background-color: #0F0F0F; border-bottom: 1px solid #1A1A1A;")
        self.top_bar.setFixedHeight(55)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)
        
        self.title_label = QLabel("MEDIA GALLERY")
        self.title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #888888; letter-spacing: 1px;")
        
        self.close_btn = QPushButton("✖ CLOSE")
        self.close_btn.setFixedSize(110, 36)
        self.close_btn.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.close_btn.setStyleSheet("""
            QPushButton { background-color: #222222; color: #FFFFFF; border-radius: 18px; }
            QPushButton:pressed { background-color: #444444; }
        """)
        self.close_btn.clicked.connect(self.close)
        
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.close_btn)
        outer_layout.addWidget(self.top_bar)
        
        # --- Center View Framework ---
        self.view_stack = QWidget()
        stack_layout = QVBoxLayout(self.view_stack)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.setSpacing(0)
        
        # 1. Image Previews Grid Layout
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(15, 15, 15, 15)
        self.grid_layout.setSpacing(15)
        
        self.slots = []
        for i in range(self.page_size):
            frame = QFrame()
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(4, 4, 4, 4)
            
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("background-color: #0A0A0A; border-radius: 4px;")
            lbl.setScaledContents(False)  # Lock layout scaling artifacts completely out
            frame_layout.addWidget(lbl)
            
            self.grid_layout.addWidget(frame, i // 2, i % 2)
            self.slots.append((frame, lbl))
            
        # 2. Immersive View Screen Layout
        self.fullscreen_label = QLabel()
        self.fullscreen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fullscreen_label.setStyleSheet("background-color: #000000;")
        self.fullscreen_label.setScaledContents(False)
        self.fullscreen_label.hide()
        
        stack_layout.addWidget(self.grid_widget, stretch=1)
        stack_layout.addWidget(self.fullscreen_label, stretch=1)
        outer_layout.addWidget(self.view_stack, stretch=1)

    def load_images(self):
        """Discovers file layout quickly without reading individual file buffers."""
        extensions = ('*.jpg', '*.jpeg', '*.png', '*.mp4', '*.avi')
        self.media_files = []
        for ext in extensions:
            self.media_files.extend(glob.glob(os.path.join(self.capture_folder, ext)))
        
        self.media_files.sort(key=os.path.getmtime, reverse=True)
        
        self.global_index = 0
        self.is_fullscreen_active = False
        self.pixmap_cache.clear()
        
        self.grid_widget.show()
        self.fullscreen_label.hide()
        
        # Immediate presentation loop initialization
        self.manage_lazy_cache_loading()
        self.render_view()

    def manage_lazy_cache_loading(self):
        """Loads assets contextually for the visible window space instead of loading the entire directory."""
        if not self.media_files:
            return
            
        current_page = self.global_index // self.page_size
        start_idx = current_page * self.page_size
        # Cache the current visible page items + the next lookahead page block elements
        end_idx = min(len(self.media_files), start_idx + (self.page_size * 2))
        
        # Calculate single cell sizing boxes accurately based on screen layout specs
        screen_size = self.parent().size() if self.parent() else QSize(800, 480)
        cell_target_size = QSize(screen_size.width() // 2 - 30, screen_size.height() // 2 - 50)
        
        for idx in range(start_idx, end_idx):
            filepath = self.media_files[idx]
            filename = os.path.basename(filepath).lower()
            is_video = filename.endswith(('.mp4', '.avi'))
            
            if not is_video and filepath not in self.pixmap_cache:
                worker = CacheRunnable(filepath, cell_target_size)
                worker.signals.result_ready.connect(self.on_cache_item_decoded)
                self.thread_pool.start(worker)

    @pyqtSlot(str, QPixmap)
    def on_cache_item_decoded(self, filepath, pixmap):
        self.pixmap_cache[filepath] = pixmap
        if not self.is_fullscreen_active:
            current_page = self.global_index // self.page_size
            page_start_idx = current_page * self.page_size
            try:
                item_idx = self.media_files.index(filepath)
                if page_start_idx <= item_idx < page_start_idx + self.page_size:
                    self.render_view()
            except ValueError:
                pass

    def set_gallery_zoom(self, direction):
        if not self.media_files or self.is_fullscreen_active:
            return

        old_page = self.global_index // self.page_size

        if direction == "in":
            if self.global_index < len(self.media_files) - 1:
                self.global_index += 1
        elif direction == "out":
            if self.global_index > 0:
                self.global_index -= 1

        new_page = self.global_index // self.page_size
        if old_page != new_page:
            # Shift lazy frame loading target blocks as the viewport scrolls
            self.manage_lazy_cache_loading()

        self.render_view()

    def handle_button_press(self):
        if not self.media_files:
            return

        if not self.is_fullscreen_active:
            self.is_fullscreen_active = True
            self.grid_widget.hide()
            self.top_bar.hide()  
            self.fullscreen_label.show()
            
            filepath = self.media_files[self.global_index]
            filename = os.path.basename(filepath).lower()
            
            if filename.endswith(('.mp4', '.avi')):
                self.fullscreen_label.setPixmap(QPixmap())
                self.fullscreen_label.setText(f"🎬 VIDEO PLAYBACK\n{filename}")
                self.fullscreen_label.setStyleSheet("color: #EDDE5D; font-size: 18px; font-weight: bold; background: #000000;")
            else:
                # Load full-resolution image dynamically for the full-screen inspector view
                pixmap = QPixmap(filepath)
                screen_size = self.size()
                if screen_size.width() <= 10:
                    screen_size = self.parent().size() if self.parent() else QSize(800, 480)
                
                scaled = pixmap.scaled(
                    screen_size, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                self.fullscreen_label.setPixmap(scaled)
                self.fullscreen_label.setStyleSheet("background: #000000;")
        else:
            self.is_fullscreen_active = False
            self.fullscreen_label.hide()
            self.top_bar.show()
            self.grid_widget.show()
            self.render_view()

    def render_view(self):
        if not self.media_files:
            for frame, lbl in self.slots:
                lbl.setPixmap(QPixmap())
                lbl.setText("No media found.")
                frame.setStyleSheet("border: 2px solid #1A1A1A; border-radius: 8px;")
            return

        current_page = self.global_index // self.page_size
        page_start_idx = current_page * self.page_size

        for slot_idx in range(self.page_size):
            frame, lbl = self.slots[slot_idx]
            target_media_idx = page_start_idx + slot_idx
            
            if target_media_idx < len(self.media_files):
                filepath = self.media_files[target_media_idx]
                filename = os.path.basename(filepath).lower()
                
                if filename.endswith(('.mp4', '.avi')):
                    lbl.setPixmap(QPixmap())
                    lbl.setText(f"🎬 VIDEO\n{filename[:15]}")
                    lbl.setStyleSheet("color: #EDDE5D; font-size: 13px; font-weight: bold; background-color: #0A0A0A; border-radius: 6px;")
                else:
                    if filepath in self.pixmap_cache:
                        lbl.setPixmap(self.pixmap_cache[filepath])
                        lbl.setStyleSheet("background-color: #0A0A0A; border-radius: 6px;")
                    else:
                        # Safety fallback: Scale dynamically if the background thread has not loaded it yet
                        pixmap = QPixmap(filepath)
                        screen_size = self.parent().size() if self.parent() else QSize(800, 480)
                        fallback_cell_size = QSize(screen_size.width() // 2 - 30, screen_size.height() // 2 - 50)
                        
                        scaled = pixmap.scaled(
                            fallback_cell_size, 
                            Qt.AspectRatioMode.KeepAspectRatio, 
                            Qt.TransformationMode.SmoothTransformation
                        )
                        lbl.setPixmap(scaled)
                        lbl.setStyleSheet("background-color: #0A0A0A; border-radius: 6px;")
                
                if target_media_idx == self.global_index:
                    frame.setStyleSheet("border: 3px solid #26D0CE; border-radius: 8px; padding: 1px;")
                else:
                    frame.setStyleSheet("border: 3px solid #151515; border-radius: 8px; padding: 1px;")
            else:
                lbl.setPixmap(QPixmap())
                lbl.setText("")
                frame.setStyleSheet("border: 3px dashed #111111; border-radius: 8px; background-color: transparent;")

    def mousePressEvent(self, event): pass
    def mouseReleaseEvent(self, event): pass