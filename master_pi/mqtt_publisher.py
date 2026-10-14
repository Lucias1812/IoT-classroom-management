import paho.mqtt.client as mqtt

BROKER = "localhost"   # later replace with Master Pi IP if needed
PORT = 1883


def publish_message(topic, message):
    client = mqtt.Client()

    try:
        client.connect(BROKER, PORT, 60)
        client.publish(topic, message)
        client.disconnect()

        print(f"[MQTT] Published to {topic}: {message}")

    except Exception as e:
        print(f"[MQTT ERROR] {str(e)}")