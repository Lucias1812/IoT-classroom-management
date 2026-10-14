"""
mqtt_subscriber.py — General MQTT subscriber for all Agent Pi users.

Subscribes to:
  - admin/broadcast  : system-wide announcements from admin
  - room/+/status    : room status changes (wildcard for all rooms)

Incoming messages are stored in a short in-memory log so the
dashboard can display recent alerts without a page reload.
"""

import os
import threading
from collections import deque
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()

BROKER = os.getenv("MASTER_PI_IP", "localhost")
PORT   = int(os.getenv("MQTT_PORT", "1883"))

TOPICS = [
    ("admin/broadcast", 0),
    ("room/+/status",   0),
]

# In-memory store of recent messages (max 20)
# Other modules can import this to display alerts
recent_messages = deque(maxlen=20)
_lock = threading.Lock()


def get_recent_messages():
    """Return a snapshot of recent MQTT messages."""
    with _lock:
        return list(recent_messages)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Agent Pi subscriber connected.")
        for topic, qos in TOPICS:
            client.subscribe(topic, qos)
            print(f"[MQTT] Subscribed to {topic}")
    else:
        print(f"[MQTT] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    topic   = msg.topic
    message = msg.payload.decode()
    print(f"[MQTT] {topic}: {message}")

    with _lock:
        recent_messages.append({
            "topic":   topic,
            "message": message
        })


def start():
    """Start the MQTT subscriber — call this in a daemon thread."""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"[MQTT] Could not connect to broker at {BROKER}:{PORT} — {e}")
        print("[MQTT] Subscriber disabled. App will continue without MQTT.")


if __name__ == "__main__":
    start()
