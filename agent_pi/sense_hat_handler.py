try:
    from sense_hat import SenseHat

    sense = SenseHat()

    def show_fault_warning():
        print("[SENSE HAT] Showing FAULT warning")

        # red screen for warning
        sense.clear(255, 0, 0)

    def clear_warning():
        print("[SENSE HAT] Clearing warning")

        # clear display
        sense.clear()

except ImportError:
    # for Mac/local testing without Raspberry Pi hardware

    def show_fault_warning():
        print("[SENSE HAT MOCK] FAULT WARNING - RED ALERT")

    def clear_warning():
        print("[SENSE HAT MOCK] Warning cleared")