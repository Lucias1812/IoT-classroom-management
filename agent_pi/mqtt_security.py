import os
from sense_hat_handler import show_fault_warning
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

BROKER = os.getenv("MASTER_PI_IP", "localhost")
PORT   = int(os.getenv("MQTT_PORT", "1883"))
TOPIC  = "security/alerts"


def on_connect(client, userdata, flags, rc):
    print("[SECURITY] Connected")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    message = msg.payload.decode()
    print(f"[SECURITY ALERT] {message}")
    show_fault_warning()


def start():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"[SECURITY MQTT] Could not connect to broker — {e}")
        print("[SECURITY MQTT] Disabled. App will continue without security alerts.")


if __name__ == "__main__":
    start()