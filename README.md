

## Project Overview

A distributed IoT classroom management system for a university teaching building. Multiple Raspberry Pi devices operate as Agent Pis (for users/staff), Room Pis (for room access and display), and a central Master Pi. Communication uses MQTT (publish-subscribe) and Socket Programming (request-response). Data is persisted in a centralised remote MySQL database accessible only from the Master Pi.

**Three user roles:**
- **Users** (students/teachers) — register, book, use, report, and return classrooms
- **Admin** — system-wide control and broadcast via Master Pi web interface
- **Security Staff** — manage room status, receive fault alerts via Sense HAT

---

## System Architecture

```
[Laptop/Desktop]
  └── MySQL Database (piot_db)
         ↑ (TCP)
[Master Pi] ─── Flask Admin Web (port 5003)
  ├── Socket Server (port 5050) ←── Agent Pi / Room Pi requests
  └── MQTT Publisher → [Mosquitto Broker]
                              ↓
                    [Agent Pi]   [Room Pi]
                    MQTT Sub     MQTT Sub
```

### Master Pi
- Admin-only Flask web interface (port 5003)
- ZMQ socket server (port 5050) handles all business logic
- Connects to remote MySQL database
- Publishes MQTT alerts to all devices

### Agent Pi
- User/staff Flask web interface (port 5001)
- Sends all requests to Master Pi via ZMQ socket
- Subscribes to `admin/broadcast` and `security/alerts` MQTT topics
- Security staff: Sense HAT triggers visual warning on fault alerts

### Room Pi
- Classroom display Flask web interface (port 5002)
- Auto-refreshes every 10 seconds with room status, sensor readings, and today's bookings
- Validates one-time access tokens on user arrival
- Background thread pushes sensor readings to Master Pi every 10 seconds

---

## Prerequisites

- Python 3.x
- Git
- MySQL (on laptop/desktop to host the database)
- Mosquitto MQTT broker (on Master Pi or localhost for testing)

---

## Local Setup (Laptop/Desktop)

```bash
# 1. Clone the repo
git clone <repo-url>
cd group-assignment-group-21

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment files
cp master_pi/.env.example master_pi/.env
cp agent_pi/.env.example agent_pi/.env
cp room_pi/.env.example room_pi/.env
# Edit each .env file with your local values

# 5. Set up the database
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql
```

---

## Raspberry Pi Setup

Same as above, plus install the Sense HAT library:

```bash
pip install sense-hat
```

---

## Environment Configuration

Each folder has a `.env.example` file. Copy it to `.env` and fill in your values.

### `master_pi/.env`
```
MASTER_PI_PORT=5050
MQTT_BROKER=localhost
FLASK_SECRET=your_secret_key_here
```

### `agent_pi/.env`
```
MASTER_PI_IP=localhost
MASTER_PI_PORT=5050
MQTT_PORT=1883
```

### `room_pi/.env`
```
MASTER_PI_IP=localhost
MASTER_PI_PORT=5050
MQTT_PORT=1883
ROOM_ID=1
```

> **Never commit `.env` files** — they are in `.gitignore`.

---

## Running the Project (Local Testing)

Start in this order — each in a separate terminal with venv activated:

```bash
# Terminal 1 — MQTT Broker
/opt/homebrew/sbin/mosquitto -v        # Mac
mosquitto                              # Linux/Pi

# Terminal 2 — Master Pi
cd master_pi && python3 app.py

# Terminal 3 — Agent Pi
cd agent_pi && python3 app.py

# Terminal 4 — Room Pi
cd room_pi && python3 app.py
```

**Access:**
- Admin panel: http://localhost:5003 (login: `ADMIN` / `admin123`)
- Agent Pi: http://localhost:5001 (login: `S001` / `password123`)
- Room Pi display: http://localhost:5002/display

---

## Demo Day Setup (Multi-Device)

### Before leaving home
- Push all changes to GitHub
- Ensure database is seeded and working

### On the day

**1. Find the Master Pi's IP:**
```bash
hostname -I   # on Master Pi
```

**2. Update `.env` on each device** with the Master Pi's IP:
```
MASTER_PI_IP=192.168.x.x
```

**3. Allow remote DB connections** (run once on the laptop hosting MySQL):
```sql
CREATE USER 'piot_user'@'%' IDENTIFIED BY 'piot_password';
GRANT ALL PRIVILEGES ON piot_db.* TO 'piot_user'@'%';
FLUSH PRIVILEGES;
```

**4. Update `master_pi/db.py`** with the laptop's IP on the day.

**5. Start in order:**
1. MySQL on laptop
2. Mosquitto on Master Pi
3. Master Pi app
4. Room Pi app
5. Agent Pi app

---

## Running Tests

```bash
# From project root with venv activated
python -m pytest tests/ -v
```

52 tests across 5 files — no database or MQTT broker required (uses mocking).

---

## Custom Enhancements

### Enhancement 1: QR Code Room Access
A QR code is dynamically generated and displayed on the Room Pi verify token page. Users scan it with their phone camera which opens the token entry form directly on their mobile browser. This removes the need to manually type the Room Pi's URL on a phone, making room access faster and more intuitive. Implemented using the qrcode Python library in room_pi/.

### Enhancement 2: Real-Time System Health Dashboard
A live system health dashboard on the Master Pi admin panel shows all rooms in a card grid with their current sensor readings (temperature, humidity, pressure), room status with colour coding, and the time since the last sensor reading was received. Rooms are flagged as "Stale" if data is over 2 minutes old and "No Data" if no readings have ever been received. The dashboard auto-refreshes every 15 seconds. Implemented in master_pi/ with a dedicated /system_health route and template.

---

## Design Patterns

### Observer Pattern (via MQTT)
Master Pi acts as publisher; Agent Pi and Room Pi act as subscribers. Room status changes and fault alerts are broadcast automatically to all subscribed devices without direct coupling.

### State Pattern (Room Status)
Each room transitions between states: `available → in_use → fault → maintenance → available`. State transitions are managed through Master Pi logic and broadcast via MQTT.

---

## Challenges Encountered

- MQTT broker setup and graceful error handling when broker unavailable
- Flask route management across multiple Pis on different ports
- Synchronising socket communication and MQTT events
- JSON serialisation of MySQL `Decimal` types from sensor readings
- Managing GitHub collaboration across the group

---

## Lessons Learned

- Distributed IoT systems require careful communication design upfront
- MQTT is highly effective for real-time one-to-many event handling
- Socket programming works best for direct request-response communication
- Mocking external dependencies makes unit tests reliable and fast
- Proper Git workflow (branches + PRs) prevents major integration issues
