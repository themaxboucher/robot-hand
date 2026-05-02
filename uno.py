"""Servo smoke test: drive all four servos to 0, 90, then 180 degrees in a loop."""

import sys
import time

import serial
from serial.tools import list_ports


SERVO_PINS = (2, 3, 4, 5)
NUM_SERVOS = len(SERVO_PINS)
BAUD = 115200
SETTLE_SECONDS = 2.0
HOLD_SECONDS = 1.0
ANGLES = (0, 90, 180)


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


def send_all(ser, angle):
    payload = ",".join([str(angle)] * NUM_SERVOS) + "\n"
    ser.write(payload.encode("ascii"))


def main():
    port = find_arduino_port()
    if not port:
        print("Could not auto-detect an Arduino.", file=sys.stderr)
        return 1

    with serial.Serial(port, BAUD, timeout=1) as ser:
        # Opening the serial port resets the Uno; wait for the bootloader.
        time.sleep(SETTLE_SECONDS)
        print(f"Connected to Arduino on {port}. Cycling 0 -> 90 -> 180. Ctrl+C to stop.")

        try:
            while True:
                for angle in ANGLES:
                    print(f"Servos -> {angle}")
                    send_all(ser, angle)
                    time.sleep(HOLD_SECONDS)
        except KeyboardInterrupt:
            print("\nStopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
