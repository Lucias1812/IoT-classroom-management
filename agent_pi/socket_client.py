import zmq
import os
from dotenv import load_dotenv

load_dotenv()

MASTER_PI_IP = os.getenv("MASTER_PI_IP", "localhost")
MASTER_PI_PORT = os.getenv("MASTER_PI_PORT", "5050")

context = zmq.Context()


def send_request(action: str, data: dict = {}) -> dict:
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    socket.connect(f"tcp://{MASTER_PI_IP}:{MASTER_PI_PORT}")
    try:
        payload = {"action": action, "data": data}
        print(f"[CLIENT] Sending: {payload}")
        socket.send_json(payload)
        response = socket.recv_json()
        print(f"[CLIENT] Received: {response}")
        return response
    except zmq.error.Again:
        return {"status": "error", "message": "Master Pi timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        socket.close()


# ── convenience functions ──────────────────────────────

def ping():
    return send_request("ping")

def login(university_id: str, password: str):
    return send_request("login", {
        "university_id": university_id,
        "password": password
    })

def register(university_id: str, full_name: str, email: str, password: str):
    return send_request("register", {
        "university_id": university_id,
        "full_name": full_name,
        "email": email,
        "password": password
    })

def search_rooms(date: str, start_time: str, end_time: str):
    return send_request("search_rooms", {
        "date": date,
        "start_time": start_time,
        "end_time": end_time
    })

def book_room(user_id: int, room_id: int, date: str, start_time: str, end_time: str):
    return send_request("book_room", {
        "user_id": user_id,
        "room_id": room_id,
        "date": date,
        "start_time": start_time,
        "end_time": end_time
    })

def cancel_booking(booking_id: int, user_id: int):
    return send_request("cancel_booking", {
        "booking_id": booking_id,
        "user_id": user_id
    })

def checkin(booking_id: int, user_id: int):
    return send_request("checkin", {
        "booking_id": booking_id,
        "user_id": user_id
    })

def checkout(booking_id: int, user_id: int):
    return send_request("checkout", {
        "booking_id": booking_id,
        "user_id": user_id
    })

def validate_token(token: str, room_id: int):
    return send_request("validate_token", {
        "token": token,
        "room_id": room_id
    })

def report_fault(room_id: int, user_id: int, description: str):
    return send_request("report_fault", {
        "room_id": room_id,
        "user_id": user_id,
        "description": description
    })

def update_room_status(room_id: int, new_status: str, changed_by: int):
    return send_request("update_status", {
        "room_id": room_id,
        "new_status": new_status,
        "changed_by": changed_by
    })

def get_bookings(user_id: int):
    return send_request("get_bookings", {
        "user_id": user_id
    })


