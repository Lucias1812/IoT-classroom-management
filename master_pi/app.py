import threading
import hashlib
import os
from flask import Flask, render_template, request, redirect, session, send_file
from db import get_connection
from mqtt_publisher import publish_message
from report_generator import generate_report
from socket_server import start as start_socket_server

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "master_pi_secret_key")


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def admin_required(f):
    """Decorator: redirect to login if not an authenticated admin."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


# --------------------------------------------------
# AUTH
# --------------------------------------------------

@app.route("/")
def home():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        university_id = request.form.get("university_id", "").strip()
        password      = request.form.get("password", "")

        if not university_id or not password:
            return render_template("login.html", error="All fields are required.")

        conn = get_connection()
        if conn is None:
            return render_template("login.html", error="Database connection failed.")

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, full_name, role FROM users "
                "WHERE university_id = %s AND password_hash = %s AND role = 'admin'",
                (university_id, hash_password(password))
            )
            user = cursor.fetchone()
            cursor.close()
        finally:
            conn.close()

        if not user:
            return render_template("login.html", error="Invalid credentials or not an admin account.")

        session["user_id"]   = user["id"]
        session["full_name"] = user["full_name"]
        session["role"]      = user["role"]
        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
@admin_required
def dashboard():
    conn = get_connection()
    stats = {}
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'user'")
            stats["users"] = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS total FROM bookings WHERE status = 'active'")
            stats["active_bookings"] = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS total FROM fault_reports WHERE status = 'pending'")
            stats["pending_faults"] = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS total FROM rooms")
            stats["rooms"] = cursor.fetchone()["total"]
            cursor.close()
        finally:
            conn.close()
    return render_template("dashboard.html", stats=stats, full_name=session["full_name"])


# --------------------------------------------------
# USER MANAGEMENT
# --------------------------------------------------

@app.route("/users")
@admin_required
def users():
    conn = get_connection()
    all_users = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, university_id, full_name, email, role, created_at "
                "FROM users ORDER BY role, full_name"
            )
            all_users = cursor.fetchall()
            cursor.close()
        finally:
            conn.close()
    return render_template("users.html", users=all_users)


@app.route("/users/create", methods=["GET", "POST"])
@admin_required
def create_user():
    if request.method == "POST":
        university_id = request.form.get("university_id", "").strip()
        full_name     = request.form.get("full_name", "").strip()
        email         = request.form.get("email", "").strip()
        password      = request.form.get("password", "")
        role          = request.form.get("role", "security")

        if not all([university_id, full_name, email, password]):
            return render_template("create_user.html", error="All fields are required.")

        conn = get_connection()
        if conn is None:
            return render_template("create_user.html", error="Database connection failed.")

        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (university_id, full_name, email, password_hash, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (university_id, full_name, email, hash_password(password), role)
            )
            conn.commit()
            cursor.close()
        except Exception as e:
            conn.close()
            return render_template("create_user.html", error=f"Failed to create user: {e}")
        finally:
            conn.close()

        return redirect("/users")

    return render_template("create_user.html")


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = %s AND role != 'admin'", (user_id,))
            conn.commit()
            cursor.close()
        finally:
            conn.close()
    return redirect("/users")


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    conn = get_connection()
    if conn is None:
        return redirect("/users")

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email     = request.form.get("email", "").strip()
        role      = request.form.get("role", "user")

        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET full_name = %s, email = %s, role = %s WHERE id = %s",
                (full_name, email, role, user_id)
            )
            conn.commit()
            cursor.close()
        finally:
            conn.close()
        return redirect("/users")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
    finally:
        conn.close()

    if not user:
        return redirect("/users")

    return render_template("edit_user.html", user=user)


# --------------------------------------------------
# BOOKINGS & LOGS
# --------------------------------------------------

@app.route("/bookings")
@admin_required
def bookings():
    conn = get_connection()
    booking_list = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT b.id, u.full_name AS user_name, u.university_id,
                       r.room_code, b.date, b.start_time, b.end_time, b.status,
                       b.created_at
                FROM bookings b
                JOIN users u ON b.user_id = u.id
                JOIN rooms r ON b.room_id = r.id
                ORDER BY b.date DESC, b.start_time DESC
                LIMIT 100
            """)
            booking_list = cursor.fetchall()
            # Convert timedelta to string
            for row in booking_list:
                for key in ("start_time", "end_time"):
                    val = row.get(key)
                    if val and hasattr(val, "seconds"):
                        total = int(val.total_seconds())
                        row[key] = f"{total // 3600:02}:{(total % 3600) // 60:02}"
                if row.get("date"):
                    row["date"] = str(row["date"])
            cursor.close()
        finally:
            conn.close()
    return render_template("bookings.html", bookings=booking_list)


@app.route("/logs")
@admin_required
def logs():
    conn = get_connection()
    log_list = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT al.id, u.full_name, u.university_id,
                       al.action, al.detail, al.logged_at
                FROM action_logs al
                LEFT JOIN users u ON al.user_id = u.id
                ORDER BY al.logged_at DESC
                LIMIT 100
            """)
            log_list = cursor.fetchall()
            cursor.close()
        finally:
            conn.close()
    return render_template("logs.html", logs=log_list)


# --------------------------------------------------
# ROOMS
# --------------------------------------------------

@app.route("/rooms")
@admin_required
def rooms():
    conn = get_connection()
    room_list = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, room_code, building, capacity, status, updated_at "
                "FROM rooms ORDER BY building, room_code"
            )
            room_list = cursor.fetchall()
            cursor.close()
        finally:
            conn.close()
    return render_template("rooms.html", rooms=room_list)


@app.route("/rooms/<int:room_id>/status", methods=["POST"])
@admin_required
def update_room_status(room_id):
    new_status = request.form.get("status")
    valid = {"available", "in_use", "maintenance", "fault"}
    if new_status not in valid:
        return redirect("/rooms")

    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT status FROM rooms WHERE id = %s", (room_id,))
            row = cursor.fetchone()
            old_status = row["status"] if row else "unknown"

            cursor.execute("UPDATE rooms SET status = %s WHERE id = %s", (new_status, room_id))
            cursor.execute(
                "INSERT INTO room_status_log (room_id, changed_by, old_status, new_status, reason) "
                "VALUES (%s, %s, %s, %s, 'Admin update')",
                (room_id, session["user_id"], old_status, new_status)
            )
            conn.commit()
            cursor.close()

            publish_message(f"room/{room_id}/status", new_status)

            if new_status == "fault":
                cursor2 = conn.cursor(dictionary=True)
                cursor2.execute("SELECT room_code FROM rooms WHERE id = %s", (room_id,))
                r = cursor2.fetchone()
                cursor2.close()
                if r:
                    publish_message(
                        "security/alerts",
                        f"Room {r['room_code']} is now FAULT status - admin alert"
                    )
        finally:
            conn.close()

    return redirect("/rooms")


# --------------------------------------------------
# FAULT REPORTS
# --------------------------------------------------

@app.route("/faults")
@admin_required
def faults():
    conn = get_connection()
    fault_list = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT fr.id, r.room_code, u.full_name AS reported_by,
                       fr.description, fr.status, fr.created_at,
                       r.id AS room_id
                FROM fault_reports fr
                JOIN rooms r  ON fr.room_id = r.id
                JOIN users u  ON fr.reported_by = u.id
                ORDER BY fr.status = 'pending' DESC, fr.created_at DESC
            """)
            fault_list = cursor.fetchall()
            cursor.close()
        finally:
            conn.close()
    return render_template("faults.html", faults=fault_list)


@app.route("/faults/<int:fault_id>/review", methods=["POST"])
@admin_required
def review_fault(fault_id):
    decision    = request.form.get("decision")          # 'confirmed' or 'dismissed'
    announcement = request.form.get("announcement", "").strip()

    if decision not in ("confirmed", "dismissed"):
        return redirect("/faults")

    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # Get fault + room info before updating
            cursor.execute("""
                SELECT fr.room_id, r.room_code
                FROM fault_reports fr
                JOIN rooms r ON fr.room_id = r.id
                WHERE fr.id = %s
            """, (fault_id,))
            fault = cursor.fetchone()

            cursor.execute(
                "UPDATE fault_reports SET status = %s, reviewed_by = %s, reviewed_at = NOW() "
                "WHERE id = %s",
                (decision, session["user_id"], fault_id)
            )

            if decision == "confirmed" and fault:
                # Update room to fault/maintenance and broadcast
                cursor.execute(
                    "UPDATE rooms SET status = 'fault' WHERE id = %s", (fault["room_id"],)
                )
                msg = announcement if announcement else \
                    f"Room {fault['room_code']} is down, waiting for maintenance"
                publish_message("admin/broadcast", msg)
                publish_message(f"room/{fault['room_id']}/status", "fault")
                publish_message("security/alerts", msg)

            conn.commit()
            cursor.close()
        finally:
            conn.close()

    return redirect("/faults")


# --------------------------------------------------
# REPORTS
# --------------------------------------------------

@app.route("/reports")
@admin_required
def reports():
    return render_template("reports.html")


@app.route("/reports/generate", methods=["POST"])
@admin_required
def generate_report_route():
    conn = get_connection()
    if conn is None:
        return render_template("reports.html", error="Database connection failed.")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.room_code, COUNT(b.id) AS booking_count
            FROM rooms r
            LEFT JOIN bookings b ON r.id = b.room_id
            GROUP BY r.id, r.room_code
            ORDER BY booking_count DESC
        """)
        data = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    rooms_labels   = [row["room_code"]     for row in data]
    booking_counts = [row["booking_count"] for row in data]

    path = generate_report(rooms_labels, booking_counts)
    return render_template("reports.html", report_generated=True, report_path=path)


@app.route("/reports/download")
@admin_required
def download_report():
    path = os.path.join(os.path.dirname(__file__), "report.png")
    if os.path.exists(path):
        return send_file(path, mimetype="image/png", as_attachment=True,
                         download_name="room_usage_report.png")
    return redirect("/reports")


# --------------------------------------------------
# SYSTEM HEALTH
# --------------------------------------------------
 
@app.route("/health")
@admin_required
def health():
    """
    System health dashboard.
    Shows each room's Pi connectivity status and sensor freshness
    based on the most recent sensor reading in the database.
    """
    conn = get_connection()
    rooms = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT
                    r.id,
                    r.room_code,
                    r.building,
                    r.status,
                    sr.temperature,
                    sr.humidity,
                    sr.pressure,
                    sr.recorded_at AS last_seen,
                    TIMESTAMPDIFF(SECOND, sr.recorded_at, NOW()) AS age_seconds
                FROM rooms r
                LEFT JOIN (
                    SELECT room_id,
                           temperature, humidity, pressure, recorded_at,
                           ROW_NUMBER() OVER (PARTITION BY room_id ORDER BY recorded_at DESC) AS rn
                    FROM sensor_readings
                ) sr ON sr.room_id = r.id AND sr.rn = 1
                ORDER BY r.building, r.room_code
            """)
            rooms = cursor.fetchall()
            # Convert datetime to string for template
            for row in rooms:
                if row.get("last_seen"):
                    row["last_seen"] = str(row["last_seen"])
            cursor.close()
        finally:
            conn.close()
 
    # Build summary counts
    online  = sum(1 for r in rooms if r["age_seconds"] is not None and r["age_seconds"] <= 120)
    stale   = sum(1 for r in rooms if r["age_seconds"] is not None and r["age_seconds"] > 120)
    offline = sum(1 for r in rooms if r["age_seconds"] is None)
 
    summary = {
        "online":  online,
        "stale":   stale,
        "offline": offline,
        "total":   len(rooms),
    }
 
    return render_template("health.html", rooms=rooms, summary=summary)

# --------------------------------------------------
# ENTRY POINT — run Flask + socket server together
# --------------------------------------------------

if __name__ == "__main__":
    # Socket server runs in a background daemon thread
    socket_thread = threading.Thread(target=start_socket_server, daemon=True)
    socket_thread.start()
    print("[MASTER PI] Socket server started in background thread")

    # Flask admin web interface on port 5000
    app.run(debug=False, host="0.0.0.0", port=5003)
