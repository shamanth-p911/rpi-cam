import json
import os
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
        
        # Load local fallback defaults directly to prevent silent idle loops
        self.config = {
            "enabled": True,
            "broker": "192.168.100.168",
            "port": 1883,
            "topic": "camera/commands",
            "username": "",
            "password": "",
            "client_id": "rpicam_client"
        }
        self._load_local_config_fallback()

    def _load_local_config_fallback(self):
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mqtt_config.json")
            if not os.path.exists(config_path):
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mqtt_config.json")
                
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    data = json.load(f)
                    active_profile_name = data.get("active_profile", "DefaultProfile")
                    for prof in data.get("profiles", []):
                        if prof.get("network_name") == active_profile_name:
                            self.config.update(prof)
                            print(f"[MQTT] Worker auto-loaded profile: {active_profile_name}")
                            break
        except Exception as e:
            print(f"[MQTT] Could not auto-load config: {e}")

    def apply_config(self, new_config):
        print(f"[MQTT] Applying new config configuration parameters...")
        self.config.update(new_config)
        if self.client and self.client.is_connected():
            print("[MQTT] Config updated, hot-reconnecting client...")
            self.client.disconnect()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        status_code = rc.value if hasattr(rc, 'value') else rc
        if status_code == 0:
            print(f"[MQTT] Connected successfully to broker: {self.config['broker']}")
            self.mqtt_connected.emit()
            
            # CRITICAL: Always subscribe immediately upon a successful handshake connection
            target_topic = self.config.get("topic", "camera/commands")
            client.subscribe(target_topic, qos=1)
            print(f"[MQTT] Subscribed to command pathway channel: '{target_topic}'")
        else:
            print(f"[MQTT] Connection failed with status branch code: {status_code}")
            self.mqtt_error.emit(f"Connection failed: code {status_code}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        print("[MQTT] Disconnected from network broker hub.")
        self.mqtt_disconnected.emit()

    def _on_message(self, client, userdata, msg):
        try:
            payload_str = msg.payload.decode("utf-8")
            print(f"[MQTT] Received inbound message packet: {payload_str} on topic {msg.topic}")
            self.mqtt_message_received.emit(payload_str)
            
            data = json.loads(payload_str)
            action = data.get("action")
            
            if action == "take_photo":
                print("[MQTT] Routing event: Capture High-Res Frame")
                self.photo_requested.emit()
            elif action == "start_video":
                print("[MQTT] Routing event: Initialize Video Recording Stream")
                self.video_start_requested.emit()
            elif action == "stop_video":
                print("[MQTT] Routing event: Terminate Video Recording Stream")
                self.video_stop_requested.emit()
                
        except Exception as e:
            print(f"[MQTT Processing Error] Failed to parse payload context: {e}")

    # FIXED: Renamed from run_worker_loop to start_listening to match main.py line 163
    def start_listening(self):
        print("[MQTT] Worker background monitoring process thread active.")
        
        while self.running:
            if self.config.get("enabled", False):
                if self.client is None or not self.client.is_connected():
                    print(f"[MQTT] Connection loop targeting broker -> {self.config['broker']}:{self.config['port']}")
                    try:
                        try:
                            self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
                        except AttributeError:
                            try:
                                self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION_2)
                            except AttributeError:
                                self.client = mqtt.Client()
                        
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
                        
                        QThread.msleep(1000)
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