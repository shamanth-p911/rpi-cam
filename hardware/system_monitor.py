import shutil
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class SystemMonitorWorker(QObject):
    status_updated = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.running = True

    def start_monitoring(self):
        print("[MONITOR] Telemetry loop initialized.")
        while self.running:
            storage_pct = 0.0
            try:
                total, used, free = shutil.disk_usage("/")
                storage_pct = (used / total) * 100.0
            except Exception:
                pass

            battery_pct = 95.0 
            self.status_updated.emit(battery_pct, storage_pct)
            
            for _ in range(50):
                if not self.running: break
                QThread.msleep(100)

        print("[MONITOR] Telemetry engine shut down cleanly.")

    def stop(self):
        self.running = False