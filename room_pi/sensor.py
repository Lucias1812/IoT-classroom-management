"""
sensor.py — reads temperature, humidity, and pressure.

On a real Raspberry Pi with Sense HAT attached this uses the
sense_hat library. On any other machine (Mac, CI, local dev)
it falls back to simulated readings so the rest of the app
still runs without hardware.
"""

import random

try:
    from sense_hat import SenseHat
    _sense = SenseHat()
    _HAS_HARDWARE = True
    print("[SENSOR] Sense HAT detected — using real sensor readings.")
except ImportError:
    _sense = None
    _HAS_HARDWARE = False
    print("[SENSOR] Sense HAT not found — using simulated sensor readings.")


def read_sensor() -> dict:
    """
    Return a dict with temperature, humidity, and pressure.
    Uses real Sense HAT readings when available, otherwise simulates.
    """
    if _HAS_HARDWARE:
        return {
            "temperature": round(_sense.get_temperature(), 2),
            "humidity":    round(_sense.get_humidity(), 2),
            "pressure":    round(_sense.get_pressure(), 2),
        }

    # Simulated readings — realistic university classroom values
    return {
        "temperature": round(random.uniform(20.0, 26.0), 2),
        "humidity":    round(random.uniform(40.0, 65.0), 2),
        "pressure":    round(random.uniform(1008.0, 1020.0), 2),
    }
