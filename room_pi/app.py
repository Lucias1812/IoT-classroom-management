import threading
import time
from flask import Flask, render_template, request
from socket_client import (
    get_room_info,
    validate_token,
    save_sensor_reading,
    report_fault
)
from sensor import read_sensor

app = Flask(__name__)

# Each Room Pi has a fixed room ID — set via environment or hardcode per device
ROOM_ID = 1


# --------------------------------------------------
# BACKGROUND SENSOR PUSH
# Every 10 seconds read sensors and push to Master Pi
# --------------------------------------------------

def sensor_loop():
    """Background thread: read sensors every 10s and save to Master Pi."""
    while True:
        try:
            reading = read_sensor()
            save_sensor_reading(
                room_id=ROOM_ID,
                temperature=reading["temperature"],
                humidity=reading["humidity"],
                pressure=reading["pressure"]
            )
        except Exception as e:
            print(f"[SENSOR LOOP ERROR] {e}")
        time.sleep(10)


# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.route("/")
def home():
    return redirect_to_display()


def redirect_to_display():
    from flask import redirect
    return redirect("/display")


@app.route("/display")
def display():
    """
    Main room display page — shows status, sensor readings,
    and today's booking schedule. Auto-refreshes every 10s.
    """
    response = get_room_info(ROOM_ID)

    if response.get("status") != "ok":
        return render_template(
            "display.html",
            error=response.get("message", "Could not load room info."),
            room_id=ROOM_ID
        )

    room     = response.get("room", {})
    bookings = response.get("bookings", [])
    sensor   = response.get("sensor", {})

    return render_template(
        "display.html",
        room=room,
        bookings=bookings,
        sensor=sensor,
        room_id=ROOM_ID
    )


@app.route("/verify_token", methods=["GET", "POST"])
def verify_token_page():
    """Room Pi token verification — user presents token on arrival."""
    result = None

    if request.method == "POST":
        token    = request.form.get("token", "").strip()
        response = validate_token(token, ROOM_ID)

        if response["status"] == "ok":
            result = {
                "granted": True,
                "user":     response.get("user", ""),
                "end_time": response.get("end_time", "")
            }
        else:
            result = {
                "granted": False,
                "message": response.get("message", "Access denied.")
            }

    return render_template("verify_token.html", result=result, room_id=ROOM_ID)


@app.route("/report_fault", methods=["GET", "POST"])
def report_fault_page():
    """Allow room-side fault reporting."""
    success = False
    error   = None

    if request.method == "POST":
        issue    = request.form.get("issue", "").strip()
        response = report_fault(ROOM_ID, issue)

        if response["status"] == "ok":
            success = True
        else:
            error = response.get("message", "Failed to report fault.")

    return render_template(
        "report_fault.html",
        success=success,
        error=error,
        room_id=ROOM_ID
    )


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    # Start sensor background thread
    sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
    sensor_thread.start()
    print(f"[ROOM PI] Sensor loop started for room {ROOM_ID}")

    app.run(debug=True, host="0.0.0.0", port=5002)
