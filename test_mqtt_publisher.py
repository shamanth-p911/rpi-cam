# mqtttest.py
import time
import json
import paho.mqtt.client as mqtt

# --- Configuration (Points directly to your Raspberry Pi Broker Interface) ---
BROKER = "192.168.100.168"  
PORT = 1883
TOPIC = "camera/commands"
USERNAME = ""         
PASSWORD = ""         

def on_connect(client, userdata, flags, rc, properties=None):
    # Standard compatibility check for both Paho v1.x and v2.x connection outputs
    status_code = rc.value if hasattr(rc, 'value') else rc
    if status_code == 0:
        print("\n[TESTER] Successfully connected to MQTT Broker!")
        print(f"[TESTER] Sending commands to broker IP: {BROKER} on topic: '{TOPIC}'")
    else:
        print(f"\n[TESTER] Connection refused by broker. Status code: {status_code}")

# --- 1. Instantiate the Client Object Safely across Library updates ---
try:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION_2)
    except AttributeError:
        client = mqtt.Client()

# --- 2. Bind hooks ---
if USERNAME:
    client.username_pw_set(USERNAME, PASSWORD)

client.on_connect = on_connect

# --- 3. Establish Persistent Thread Connection ---
print(f"[TESTER] Connecting to broker service at {BROKER}:{PORT}...")
try:
    client.connect(BROKER, PORT, 60)
except Exception as e:
    print(f"\n[⚠️] Failed to even reach the broker: {e}")
    print("Please make sure Mosquitto service is running on the Pi via: sudo systemctl start mosquitto")
    exit(1)

client.loop_start()
time.sleep(0.5) # Brief pause to allow the handshake network stream to initialize

try:
    while True:
        print("\n======================================")
        print(" SELECT AN MQTT COMMAND TO INJECT:")
        print(" 1 -> Trigger High-Res Photo Capture")
        print(" 2 -> Start Video Recording")
        print(" 3 -> Stop Video Recording")
        print(" 4 -> Exit Tester")
        print("======================================")
        
        choice = input("Enter option (1-4): ").strip()
        
        if choice == "1":
            payload = {"action": "take_photo"}
            client.publish(TOPIC, json.dumps(payload), qos=1)
            print(f"[TESTER] Published 'take_photo' packet to topic '{TOPIC}'")
            
        elif choice == "2":
            payload = {"action": "start_video"}
            client.publish(TOPIC, json.dumps(payload), qos=1)
            print(f"[TESTER] Published 'start_video' packet to topic '{TOPIC}'")
            
        elif choice == "3":
            payload = {"action": "stop_video"}
            client.publish(TOPIC, json.dumps(payload), qos=1)
            print(f"[TESTER] Published 'stop_video' packet to topic '{TOPIC}'")
            
        elif choice == "4":
            print("[TESTER] Shutting down connection window loops...")
            break
        else:
            print("[⚠️] Invalid selection. Please enter 1, 2, 3, or 4.")
            
        time.sleep(0.4)

finally:
    client.loop_stop()
    client.disconnect()
    print("[TESTER] Disconnected.")