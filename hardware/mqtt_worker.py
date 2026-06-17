import json
import time
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

class MQTTWorker(QObject):
    photo_requested = pyqtSignal()
    video_start_requested = pyqtSignal()
    video_stop_requested = pyqtSignal()
    
    mqtt_connected = pyqtSignal()
    mqtt_disconnected = pyqtSignal()
    mqtt_error = pyqtSignal(str)
    mqtt_message_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.client = None
        
        self.config = {
            "enabled": False,
            "broker": "",
            "port": 1883,
            "topic": "camera/commands",
            "username": "",
            "password": "",
            "client_id": "rpicam_client"
        }

    def apply_config(self, new_config):
        self.config.update(new_config)
        if self.client and self.client.is_connected():
            self.client.disconnect()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.mqtt_connected.emit()
            if self.config.get("topic"):
                self.client.subscribe(self.config["topic"])
        else:
            self.mqtt_error.emit(f"Conn Failed: {reason_code}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.mqtt_disconnected.emit()

    def _on_message(self, client, userdata, msg):
        payload_str = msg.payload.decode('utf-8').strip()
        self.mqtt_message_received.emit(payload_str)
        
        command = ""
        try:
            data = json.loads(payload_str)
            command = data.get("command", "").lower()
        except json.JSONDecodeError:
            command = payload_str.lower()

        if command in ["photo", "capture"]:
            self.photo_requested.emit()
        elif command in ["video_start", "record"]:
            self.video_start_requested.emit()
        elif command in ["video_stop", "stop"]:
            self.video_stop_requested.emit()

    def run_loop(self):
        """Main thread loop for QThread"""
        print("[MQTT] Network worker initialized.")
        while self.running:
            if self.config.get("enabled", False) and self.config.get("broker"):
                if self.client is None:
                    try:
                        self.client = mqtt.Client(
                            CallbackAPIVersion.VERSION2, 
                            client_id=self.config.get("client_id", "")
                        )
                        if self.config.get("username"):
                            self.client.username_pw_set(
                                self.config["username"], 
                                self.config.get("password", "")
                            )
                            
                        self.client.on_connect = self._on_connect
                        self.client.on_disconnect = self._on_disconnect
                        self.client.on_message = self._on_message
                        
                        self.client.connect(
                            self.config["broker"], 
                            int(self.config.get("port", 1883)), 
                            keepalive=60
                        )
                        self.client.loop_start()
                    except Exception as e:
                        self.mqtt_error.emit(str(e))
                        self.client = None
                        QThread.sleep(5)
            else:
                if self.client:
                    self.client.loop_stop()
                    self.client.disconnect()
                    self.client = None
            
            QThread.msleep(500)
            
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        print("[MQTT] Network worker shut down cleanly.")

    def stop(self):
        self.running = False