from PyQt6.QtCore import QObject, pyqtSignal, QThread

class GPIOWorker(QObject):
    rotated_clockwise = pyqtSignal()
    rotated_counter_clockwise = pyqtSignal()
    button_pressed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running = True
        self.ROTARY_PIN_A = 17 
        self.ROTARY_PIN_B = 27
        self.BUTTON_PIN = 22

    def monitor_pins(self):
        try:
            from gpiozero import RotaryEncoder, Button
            self.encoder = RotaryEncoder(self.ROTARY_PIN_A, self.ROTARY_PIN_B, max_steps=0)
            self.shutter_btn = Button(self.BUTTON_PIN, bounce_time=0.05)
            
            self.encoder.when_rotated_clockwise = lambda: self.rotated_clockwise.emit()
            self.encoder.when_rotated_counter_clockwise = lambda: self.rotated_counter_clockwise.emit()
            self.shutter_btn.when_pressed = lambda: self.button_pressed.emit()
            
            while self.running:
                QThread.msleep(100)
                
        except Exception as e:
            print(f"[GPIO Workaround] Missing drivers, running in software emulation mode: {e}")
            while self.running:
                QThread.msleep(500)

    def stop(self):
        self.running = False
