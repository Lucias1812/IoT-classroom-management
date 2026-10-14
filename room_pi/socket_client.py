import zmq
import os
from dotenv import load_dotenv

load_dotenv()

MASTER_PI_IP = os.getenv("MASTER_PI_IP", "localhost")
MASTER_PI_PORT = os.getenv("MASTER_PI_PORT", "5050")

context = zmq.Context()


def send_request(action: str, data: dict = {}) -> dict:
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 10000)
    socket.connect(f"tcp://{MASTER_PI_IP}:{MASTER_PI_PORT}")
    try:
        payload = {"action": action, "data": data}
        print(f"[ROOM CLIENT] Sending: {payload}")
        socket.send_json(payload)
        response = socket.recv_json()
        print(f"[ROOM CLIENT] Received: {response}")
        return response
    except zmq.error.Again:
        return {"status": "error", "message": "Master Pi timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        socket.close()


def get_room_info(room_id: int):
    return send_request("get_room_info", {
        "room_id": room_id
    })

def validate_token(token: str, room_id: int):
    return send_request("validate_token", {
        "token": token,
        "room_id": room_id
    })

def save_sensor_reading(room_id: int, temperature: float, humidity: float, pressure: float):
    return send_request("save_sensor", {
        "room_id": room_id,
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure
    })

def report_fault(room_id: int, description: str):
    return send_request("report_fault", {
        "room_id": room_id,
        "user_id": None,
        "description": description
    })

