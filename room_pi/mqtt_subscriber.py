import paho.mqtt.client as mqtt

BROKER = "localhost"   # later replace with Master Pi IP
PORT = 1883
TOPIC = "room/1/status"


def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with result code {rc}")
    client.subscribe(TOPIC)
    print(f"[MQTT] Subscribed to {TOPIC}")


def on_message(client, userdata, msg):
    message = msg.payload.decode()

    print(f"[MQTT] Room Status Updated: {message}")

    # Later we can update Flask display here
    if message == "fault":
        print("⚠ ROOM IS IN FAULT STATUS")

    elif message == "in_use":
        print("ROOM IS NOW IN USE")

    elif message == "available":
        print("ROOM IS NOW AVAILABLE")


def start_mqtt():
    client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)

    client.loop_forever()


if __name__ == "__main__":
    start_mqtt()