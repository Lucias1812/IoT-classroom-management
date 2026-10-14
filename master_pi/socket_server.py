import zmq
import os
import hashlib
import re
import secrets
from dotenv import load_dotenv
from mqtt_publisher import publish_message
from db import get_connection
from datetime import date as date_type


load_dotenv()

PORT = os.getenv("MASTER_PI_PORT", "5050")


def route(action: str, data: dict) -> dict:
    handlers = {
        "ping":            handle_ping,
        "login":           handle_login,
        "register":        handle_register,
        "search_rooms":    handle_search_rooms,
        "book_room":       handle_book_room,
        "cancel_booking":  handle_cancel_booking,
        "checkin":         handle_checkin,
        "checkout":        handle_checkout,
        "validate_token":  handle_validate_token,
        "report_fault":    handle_report_fault,
        "update_status":   handle_update_status,
        "save_sensor":     handle_save_sensor,
        "get_room_info":   handle_get_room_info,
        "get_bookings":    handle_get_bookings,
    }

    handler = handlers.get(action)
    if handler is None:
        return {"status": "error", "message": f"Unknown action: {action}"}

    return handler(data)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def is_valid_email(email: str) -> bool:
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email) is not None


def timedelta_to_str(val) -> str:
    """Convert MySQL TIME timedelta to HH:MM string."""
    if val and hasattr(val, 'seconds'):
        total = int(val.total_seconds())
        return f"{total // 3600:02}:{(total % 3600) // 60:02}"
    return str(val)


def serialise(obj):
    """
    Recursively convert non-JSON-serialisable types so responses
    can be sent safely over ZMQ sockets between devices.
    Handles: datetime/date/time objects, Decimal, timedelta.
    """
    if isinstance(obj, dict):
        return {k: serialise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialise(i) for i in obj]
    if hasattr(obj, 'isoformat'):   # datetime, date, time
        return str(obj)
    if hasattr(obj, 'total_seconds'):  # timedelta
        return timedelta_to_str(obj)
    try:
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return float(obj)
    except ImportError:
        pass
    return obj


def log_action(conn, user_id, action, detail=""):
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO action_logs (user_id, action, detail) VALUES (%s, %s, %s)",
            (user_id, action, detail)
        )
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[LOG ERROR] {e}")


# --------------------------------------------------
# HANDLERS
# --------------------------------------------------

def handle_ping(data):
    return {"status": "ok", "message": "pong"}


def handle_login(data):
    university_id = data.get("university_id", "").strip()
    password      = data.get("password", "")

    if not university_id or not password:
        return {"status": "error", "message": "University ID and password are required."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, full_name, role FROM users WHERE university_id = %s AND password_hash = %s",
            (university_id, hash_password(password))
        )
        user = cursor.fetchone()
        cursor.close()

        if not user:
            return {"status": "error", "message": "Invalid university ID or password."}

        log_action(conn, user["id"], "login", f"User logged in: {university_id}")

        return serialise({
            "status": "ok",
            "user_id":   user["id"],
            "full_name": user["full_name"],
            "role":      user["role"]
        })

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        return {"status": "error", "message": "Login failed due to a server error."}
    finally:
        conn.close()


def handle_register(data):
    """
    Validates input, checks for duplicates, hashes password,
    and inserts a new user into the database.
    """
    university_id = data.get("university_id", "").strip()
    full_name     = data.get("full_name", "").strip()
    email         = data.get("email", "").strip().lower()
    password      = data.get("password", "")

    if not all([university_id, full_name, email, password]):
        return {"status": "error", "message": "All fields are required."}

    if not is_valid_email(email):
        return {"status": "error", "message": "Invalid email address format."}

    if len(password) < 8:
        return {"status": "error", "message": "Password must be at least 8 characters."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM users WHERE university_id = %s OR email = %s",
            (university_id, email)
        )
        if cursor.fetchone():
            return {"status": "error", "message": "University ID or email is already registered."}

        cursor.execute(
            """INSERT INTO users (university_id, full_name, email, password_hash, role)
               VALUES (%s, %s, %s, %s, 'user')""",
            (university_id, full_name, email, hash_password(password))
        )
        conn.commit()
        new_user_id = cursor.lastrowid
        cursor.close()

        log_action(conn, new_user_id, "register", f"New user registered: {university_id}")
        print(f"[REGISTER] {university_id} ({email})")

        return serialise({"status": "ok", "message": "Registered successfully."})

    except Exception as e:
        print(f"[REGISTER ERROR] {e}")
        return {"status": "error", "message": "Registration failed due to a server error."}
    finally:
        conn.close()


def handle_search_rooms(data):
    """
    Returns rooms that are available and have no overlapping active booking
    for the requested date and time slot.
    """
    date       = data.get("date", "").strip()
    start_time = data.get("start_time", "").strip()
    end_time   = data.get("end_time", "").strip()
    search_date = date_type.fromisoformat(str(date)) if date else None
    
    if search_date and search_date < date_type.today():
        return {"status": "error", "message": "Cannot search for rooms in the past."}

    if not all([date, start_time, end_time]):
        return {"status": "error", "message": "Date, start time, and end time are required."}

    if start_time >= end_time:
        return {"status": "error", "message": "End time must be after start time."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)

        # Rooms that are available AND have no overlapping active booking
        cursor.execute("""
            SELECT r.id, r.room_code, r.building, r.capacity, r.status
            FROM rooms r
            WHERE r.status = 'available'
              AND r.id NOT IN (
                  SELECT b.room_id FROM bookings b
                  WHERE b.date = %s
                    AND b.status = 'active'
                    AND NOT (b.end_time <= %s OR b.start_time >= %s)
              )
            ORDER BY r.room_code
        """, (date, start_time, end_time))

        rooms = cursor.fetchall()
        cursor.close()

        # MySQL TIME columns return as timedelta — convert to strings
        for room in rooms:
            for key, val in room.items():
                if hasattr(val, 'seconds'):
                    room[key] = timedelta_to_str(val)

        return serialise({"status": "ok", "rooms": rooms})

    except Exception as e:
        print(f"[SEARCH ROOMS ERROR] {e}")
        return {"status": "error", "message": "Room search failed."}
    finally:
        conn.close()


def handle_book_room(data):
    """
    Creates a booking and issues a one-time use token.
    """
    user_id    = data.get("user_id")
    room_id    = data.get("room_id")
    date       = data.get("date", "").strip()
    start_time = data.get("start_time", "").strip()
    end_time   = data.get("end_time", "").strip()

    if not all([user_id, room_id, date, start_time, end_time]):
        return {"status": "error", "message": "All booking fields are required."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)

        # Re-check availability to prevent race conditions
        cursor.execute("""
            SELECT id FROM bookings
            WHERE room_id = %s
              AND date = %s
              AND status = 'active'
              AND NOT (end_time <= %s OR start_time >= %s)
        """, (room_id, date, start_time, end_time))

        if cursor.fetchone():
            return {"status": "error", "message": "Room is no longer available for that time slot."}

        # Insert the booking
        cursor.execute("""
            INSERT INTO bookings (user_id, room_id, date, start_time, end_time, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
        """, (user_id, room_id, date, start_time, end_time))
        conn.commit()
        booking_id = cursor.lastrowid

        # Generate a unique one-time token
        token = "tok_" + secrets.token_hex(8)
        cursor.execute(
            "INSERT INTO tokens (booking_id, token, used) VALUES (%s, %s, FALSE)",
            (booking_id, token)
        )
        conn.commit()
        cursor.close()

        log_action(conn, user_id, "book_room",
                   f"Booked room {room_id} on {date} {start_time}-{end_time}, token: {token}")
        print(f"[BOOK ROOM] user={user_id} room={room_id} date={date} token={token}")

        return serialise({"status": "ok", "booking_id": booking_id, "token": token})

    except Exception as e:
        print(f"[BOOK ROOM ERROR] {e}")
        return {"status": "error", "message": "Booking failed due to a server error."}
    finally:
        conn.close()


def handle_cancel_booking(data):
    """
    Cancels a booking — only the owner can cancel their own booking.
    """
    booking_id = data.get("booking_id")
    user_id    = data.get("user_id")

    if not all([booking_id, user_id]):
        return {"status": "error", "message": "Booking ID and user ID are required."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM bookings WHERE id = %s AND user_id = %s AND status = 'active'",
            (booking_id, user_id)
        )
        if not cursor.fetchone():
            return {"status": "error", "message": "Booking not found or already cancelled."}

        cursor.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = %s",
            (booking_id,)
        )
        conn.commit()
        cursor.close()

        log_action(conn, user_id, "cancel_booking", f"Cancelled booking {booking_id}")
        print(f"[CANCEL] booking={booking_id} user={user_id}")

        return {"status": "ok", "message": "Booking cancelled successfully."}

    except Exception as e:
        print(f"[CANCEL ERROR] {e}")
        return {"status": "error", "message": "Cancellation failed due to a server error."}
    finally:
        conn.close()


def handle_checkin(data):
    """
    User checks in — sets room status to in_use and logs the change.
    """
    booking_id = data.get("booking_id")
    user_id    = data.get("user_id")

    if not all([booking_id, user_id]):
        return {"status": "error", "message": "Booking ID and user ID are required."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT room_id FROM bookings WHERE id = %s AND user_id = %s AND status = 'active'",
            (booking_id, user_id)
        )
        booking = cursor.fetchone()

        if not booking:
            return {"status": "error", "message": "Active booking not found."}

        room_id = booking["room_id"]

        cursor.execute("UPDATE rooms SET status = 'in_use' WHERE id = %s", (room_id,))
        cursor.execute("""
            INSERT INTO room_status_log (room_id, changed_by, old_status, new_status, reason)
            VALUES (%s, %s, 'available', 'in_use', 'User checked in')
        """, (room_id, user_id))
        conn.commit()
        cursor.close()

        publish_message(f"room/{room_id}/status", "in_use")
        log_action(conn, user_id, "checkin", f"Checked in room {room_id} booking {booking_id}")
        print(f"[CHECKIN] booking={booking_id} room={room_id}")

        return {"status": "ok", "message": "Checked in successfully."}

    except Exception as e:
        print(f"[CHECKIN ERROR] {e}")
        return {"status": "error", "message": "Check-in failed due to a server error."}
    finally:
        conn.close()


def handle_checkout(data):
    """
    User checks out — sets room back to available, marks booking completed.
    """
    booking_id = data.get("booking_id")
    user_id    = data.get("user_id")

    if not all([booking_id, user_id]):
        return {"status": "error", "message": "Booking ID and user ID are required."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT room_id FROM bookings WHERE id = %s AND user_id = %s AND status = 'active'",
            (booking_id, user_id)
        )
        booking = cursor.fetchone()

        if not booking:
            return {"status": "error", "message": "Active booking not found."}

        room_id = booking["room_id"]

        cursor.execute("UPDATE bookings SET status = 'completed' WHERE id = %s", (booking_id,))
        cursor.execute("UPDATE rooms SET status = 'available' WHERE id = %s", (room_id,))
        cursor.execute("""
            INSERT INTO room_status_log (room_id, changed_by, old_status, new_status, reason)
            VALUES (%s, %s, 'in_use', 'available', 'User checked out')
        """, (room_id, user_id))
        conn.commit()
        cursor.close()

        publish_message(f"room/{room_id}/status", "available")
        log_action(conn, user_id, "checkout", f"Checked out room {room_id} booking {booking_id}")
        print(f"[CHECKOUT] booking={booking_id} room={room_id}")

        return {"status": "ok", "message": "Checked out successfully."}

    except Exception as e:
        print(f"[CHECKOUT ERROR] {e}")
        return {"status": "error", "message": "Check-out failed due to a server error."}
    finally:
        conn.close()


def handle_validate_token(data):
    """
    Room Pi calls this to validate a user's one-time token on arrival.
    Marks the token as used if valid.
    """
    token   = data.get("token", "").strip()
    room_id = data.get("room_id")

    if not token or not room_id:
        return {"status": "error", "message": "Token and room ID are required."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT t.id AS token_id, t.used,
                   b.id AS booking_id, b.room_id, b.end_time, b.date, b.user_id,
                   u.full_name
            FROM tokens t
            JOIN bookings b ON t.booking_id = b.id
            JOIN users u    ON b.user_id = u.id
            WHERE t.token = %s
              AND b.room_id = %s
              AND b.status = 'active'
        """, (token, room_id))

        result = cursor.fetchone()

        if not result:
            return {"status": "failed", "message": "Invalid token or wrong room."}

        if result["used"]:
            return {"status": "failed", "message": "Token has already been used."}
        
        # Check if current time is within the booking window
        from datetime import datetime, date as date_type
        today = date_type.today()
        booking_date = result["date"]
        if not isinstance(booking_date, date_type):
            booking_date = date_type.fromisoformat(str(booking_date))

        if booking_date != today:
            return {"status": "failed", "message": "This booking is not for today."}

        now = datetime.now().time()

        def to_time(val):
            if hasattr(val, "total_seconds"):
                total = int(val.total_seconds())
                return datetime.strptime(
                    f"{total // 3600:02}:{(total % 3600) // 60:02}", "%H:%M"
                ).time()
            if isinstance(val, str):
                return datetime.strptime(val, "%H:%M").time()
            return val

        start_t = to_time(result["start_time"]) if result.get("start_time") else None
        end_t   = to_time(result["end_time"])   if result.get("end_time")   else None

        if start_t and now < start_t:
            return {
                "status": "failed",
                "message": f"Booking does not start until {start_t.strftime('%H:%M')}."
            }
        if end_t and now > end_t:
            return {"status": "failed", "message": "Booking time has already passed."}

        # Mark token as used
        cursor.execute("UPDATE tokens SET used = TRUE WHERE id = %s", (result["token_id"],))
        conn.commit()
        cursor.close()

        end_time = timedelta_to_str(result["end_time"])

        publish_message(f"room/{room_id}/status", "in_use")
        log_action(conn, result["user_id"], "validate_token",
                   f"Token validated room {room_id} booking {result['booking_id']}")
        print(f"[TOKEN] Valid - room={room_id} user={result['full_name']}")

        return serialise({
            "status":     "ok",
            "message":    "Access granted.",
            "user":       result["full_name"],
            "booking_id": result["booking_id"],
            "end_time":   end_time
        })

    except Exception as e:
        print(f"[TOKEN ERROR] {e}")
        return {"status": "error", "message": "Token validation failed."}
    finally:
        conn.close()


def handle_get_bookings(data):
    """
    Returns all bookings for a user with room details and token.
    """
    user_id = data.get("user_id")

    if not user_id:
        return {"status": "error", "message": "User ID is required."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT b.id, r.room_code, b.date, b.start_time, b.end_time,
                   b.status, t.token
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            LEFT JOIN tokens t ON t.booking_id = b.id
            WHERE b.user_id = %s
            ORDER BY b.date DESC, b.start_time DESC
        """, (user_id,))

        bookings = cursor.fetchall()
        cursor.close()

        # Convert timedelta and date fields to strings
        for booking in bookings:
            for key in ("start_time", "end_time"):
                booking[key] = timedelta_to_str(booking.get(key))
            if booking.get("date"):
                booking["date"] = str(booking["date"])

        return serialise({"status": "ok", "bookings": bookings})

    except Exception as e:
        print(f"[GET BOOKINGS ERROR] {e}")
        return {"status": "error", "message": "Failed to retrieve bookings."}
    finally:
        conn.close()


def handle_report_fault(data):
    room_id     = data.get("room_id")
    user_id     = data.get("user_id")
    description = data.get("description", "")

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fault_reports (room_id, reported_by, description, status)
            VALUES (%s, %s, %s, 'pending')
        """, (room_id, user_id, description))
        conn.commit()
        cursor.close()

        publish_message(f"room/{room_id}/status", "fault")
        publish_message("security/alerts", f"Room {room_id} FAULT: {description}")
        log_action(conn, user_id, "report_fault", f"Room {room_id}: {description}")

        return {"status": "ok", "message": "Fault reported successfully."}

    except Exception as e:
        print(f"[FAULT ERROR] {e}")
        return {"status": "error", "message": "Fault report failed."}
    finally:
        conn.close()


def handle_update_status(data):
    room_id    = data.get("room_id")
    new_status = data.get("new_status")
    changed_by = data.get("changed_by")

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM rooms WHERE id = %s", (room_id,))
        room = cursor.fetchone()
        old_status = room["status"] if room else "unknown"

        cursor.execute("UPDATE rooms SET status = %s WHERE id = %s", (new_status, room_id))
        cursor.execute("""
            INSERT INTO room_status_log (room_id, changed_by, old_status, new_status, reason)
            VALUES (%s, %s, %s, %s, 'Manual status update')
        """, (room_id, changed_by, old_status, new_status))
        conn.commit()
        cursor.close()

        publish_message(f"room/{room_id}/status", new_status)

        return {"status": "ok", "message": f"Room status updated to {new_status}."}

    except Exception as e:
        print(f"[UPDATE STATUS ERROR] {e}")
        return {"status": "error", "message": "Status update failed."}
    finally:
        conn.close()


def handle_save_sensor(data):
    """Save a sensor reading from a Room Pi to the database."""
    room_id     = data.get("room_id")
    temperature = data.get("temperature")
    humidity    = data.get("humidity")
    pressure    = data.get("pressure")

    if not room_id:
        return {"status": "error", "message": "room_id is required."}

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sensor_readings (room_id, temperature, humidity, pressure) "
            "VALUES (%s, %s, %s, %s)",
            (room_id, temperature, humidity, pressure)
        )
        conn.commit()
        cursor.close()
        print(f"[SENSOR] Saved reading for room {room_id}: "
              f"temp={temperature} humidity={humidity} pressure={pressure}")
        return {"status": "ok", "message": "Sensor data saved."}
    except Exception as e:
        print(f"[SENSOR ERROR] {e}")
        return {"status": "error", "message": "Failed to save sensor data."}
    finally:
        conn.close()


def handle_get_room_info(data):
    """
    Return room status, today's bookings, and latest sensor reading
    for a given room_id.
    """
    room_id = data.get("room_id", 1)

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor = conn.cursor(dictionary=True)

        # Room details
        cursor.execute(
            "SELECT id, room_code, building, capacity, status FROM rooms WHERE id = %s",
            (room_id,)
        )
        room = cursor.fetchone()
        if not room:
            return {"status": "error", "message": f"Room {room_id} not found."}

        # Today's bookings
        cursor.execute("""
            SELECT b.id, b.start_time, b.end_time, b.status, u.full_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.room_id = %s
              AND b.date = CURDATE()
              AND b.status = 'active'
            ORDER BY b.start_time
        """, (room_id,))
        bookings_raw = cursor.fetchall()
        bookings = []
        for b in bookings_raw:
            bookings.append({
                "start_time": timedelta_to_str(b["start_time"]),
                "end_time":   timedelta_to_str(b["end_time"]),
                "user_name":  b["full_name"],
                "status":     b["status"],
            })

        # Latest sensor reading
        cursor.execute("""
            SELECT temperature, humidity, pressure
            FROM sensor_readings
            WHERE room_id = %s
            ORDER BY recorded_at DESC
            LIMIT 1
        """, (room_id,))
        sensor = cursor.fetchone() or {
            "temperature": None,
            "humidity":    None,
            "pressure":    None
        }
        if sensor:
            sensor = {k: float(v) if v is not None else None for k, v in sensor.items()}
        cursor.close()

        return serialise({
            "status":   "ok",
            "room":     room,
            "bookings": bookings,
            "sensor":   sensor,
        })

    except Exception as e:
        print(f"[ROOM INFO ERROR] {e}")
        return {"status": "error", "message": "Failed to get room info."}
    finally:
        conn.close()


# --------------------------------------------------
# START SERVER
# --------------------------------------------------

def start():
    context = zmq.Context()
    socket  = context.socket(zmq.REP)
    socket.bind(f"tcp://0.0.0.0:{PORT}")
    print(f"[MASTER PI SERVER] Listening on port {PORT}...")

    while True:
        payload  = socket.recv_json()
        print(f"[SERVER] Received: {payload}")
        action   = payload.get("action")
        data     = payload.get("data", {})
        response = route(action, data)
        print(f"[SERVER] Sending: {response}")
        socket.send_json(response)


if __name__ == "__main__":
    start()
