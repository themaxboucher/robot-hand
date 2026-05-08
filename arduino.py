import time
import serial
from serial.tools import list_ports

BOTTOM_THUMB_PIN = 6
THUMB_PIN = 7
INDEX_PIN = 2
MIDDLE_PIN = 3
RING_PIN = 4
PINKY_PIN = 5

SERVO_PINS = (BOTTOM_THUMB_PIN, THUMB_PIN, INDEX_PIN, MIDDLE_PIN, RING_PIN, PINKY_PIN)
NUM_SERVOS = len(SERVO_PINS)

DEFAULT_BAUD = 115200 # Must match the baud rate in the Arduino code

def find_arduino_port():
    for port in list_ports.comports():
        description = f"{port.description} {port.manufacturer or ''}".lower()
        device = port.device.lower()

        if (
            "arduino" in description
            or "uno" in description
            or "wch" in description
            or "ch340" in description
            or "usbmodem" in device
            or "usbserial" in device
        ):
            return port.device
    return None

class ArduinoServos:
    def __init__(self, port=None, baud_rate=DEFAULT_BAUD, timeout=1.0, settle=2.0):
        port = port or find_arduino_port()
        if not port:
            raise RuntimeError(
                "Could not auto-detect an Arduino. Pass port=... explicitly."
            )

        self.port = port
        self._serial = serial.Serial(port, baud_rate, timeout=timeout)
        
        time.sleep(settle) # Wait for the Arduino to reboot

    def send_angles(self, angles):
        if len(angles) != NUM_SERVOS:
            raise ValueError(f"Expected {NUM_SERVOS} angles, got {len(angles)}")
        clamped = [max(0, min(180, int(a))) for a in angles]
        message = ",".join(str(a) for a in clamped) + "\n"
        self._serial.write(message.encode("ascii"))

    def close(self):
        if self._serial.is_open:
            self._serial.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

def open_close_demo(arduino, step=1, interval=0.02):
    """Slowly open and close all fingers in a loop until interrupted.

    Sends the same angle to every servo, ramping from 0° (open) up to 180°
    (closed) and back down. With the defaults below one full open-close cycle
    takes ~7.2 seconds.
    """
    print("Opening and closing all fingers. Press Ctrl+C to stop.")
    angle = 0
    direction = 1
    while True:
        arduino.send_angles([angle] * NUM_SERVOS)
        angle += direction * step
        if angle >= 180:
            angle, direction = 180, -1
        elif angle <= 0:
            angle, direction = 0, 1
        time.sleep(interval)
