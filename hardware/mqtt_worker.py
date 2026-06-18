import json
import time
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import paho.mqtt.client as mqtt

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
            print("[MQTT] Config updated, reconnecting client...")
            self.client.disconnect()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for MQTT connection events compatible with multiple Paho versions."""
        # Check both integer return codes (v1) and reason codes (v2)
        status_code = rc.value if hasattr(rc, 'value') else rc
        if status_code == 0:
            print(f"[MQTT] Connected successfully to broker: {self.config['broker']}")
            self.mqtt_connected.emit()
            if self.config.get("topic"):
                self.client.subscribe(self.config["topic"], qos=1)
                print(f"[MQTT] Subscribed to command topic: '{self.config['topic']}'")
        else:
            print(f"[MQTT] Connection rejected with status code: {status_code}")
            self.mqtt_error.emit(f"Conn rejected: {status_code}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        print("[MQTT] Disconnected from broker.")
        self.mqtt_disconnected.emit()

    def _on_message(self, client, userdata, msg):
        try:
            payload_str = msg.payload.decode('utf-8')
            print(f"[MQTT] Raw incoming message string: {payload_str}")
            self.mqtt_message_received.emit(payload_str)
            
            # Parse the incoming operational command payload
            data = json.loads(payload_str)
            action = data.get("action")
            
            print(f"[MQTT] Match action command parsed: '{action}'")
            
            if action == "take_photo":
                print("[MQTT] -> Emitting photo capture trigger signal...")
                self.photo_requested.emit()
            elif action == "start_video":
                print("[MQTT] -> Emitting video recording start signal...")
                self.video_start_requested.emit()
            elif action == "stop_video":
                print("[MQTT] -> Emitting video recording stop signal...")
                self.video_stop_requested.emit()
                
        except Exception as e:
            print(f"[MQTT Error] Failed processing message packet payload: {e}")

    def start_listening(self):
        print("[MQTT] Background networking loop thread running.")
        while self.running:
            if self.config.get("enabled"):
                if self.client is None:
                    try:
                        print(f"[MQTT] Attempting client instantiation to {self.config['broker']}:{self.config['port']}...")
                        
                        # Safe Client initialization layout matrix matching project env parameters
                        try:
                            self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, 
                                                      client_id=self.config.get("client_id", "rpicam_client"))
                        except AttributeError:
                            try:
                                self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION_2,
                                                          client_id=self.config.get("client_id", "rpicam_client"))
                            except AttributeError:
                                self.client = mqtt.Client(client_id=self.config.get("client_id", "rpicam_client"))

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
                        print(f"[MQTT Client Error] Connection error: {e}")
                        self.mqtt_error.emit(str(e))
                        self.client = None
                        QThread.sleep(5)
            else:
                if self.client:
                    print("[MQTT] Service explicitly disabled. Disconnecting client.")
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