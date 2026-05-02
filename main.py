import argparse
import math
import sys
import time

import cv2
import mediapipe as mp
import serial
from serial.tools import list_ports


SERVO_PINS = (2, 3, 4, 5)
NUM_SERVOS = len(SERVO_PINS)
DEFAULT_BAUD = 115200

# Roughly the PIP-joint angle range we see from MediaPipe in practice:
# fully curled is ~40°, fully extended is ~175°.
FINGER_ANGLE_RANGE = (40.0, 175.0)

# Cap servo updates so we don't saturate the serial link.
SERVO_SEND_HZ = 30.0


mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)


def find_arduino_port():
    """Return the first likely Arduino Uno serial port, or None."""
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
    """Send servo angles to an Arduino."""

    def __init__(self, port=None, baud_rate=DEFAULT_BAUD, timeout=1.0, settle=2.0):
        port = port or find_arduino_port()
        if not port:
            raise RuntimeError(
                "Could not auto-detect an Arduino. Pass port=... explicitly."
            )

        self.port = port
        self._serial = serial.Serial(port, baud_rate, timeout=timeout)
        # Opening the serial port resets most Uno boards; wait for the bootloader.
        time.sleep(settle)

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


def calculate_angle(a, b, c):
    """
    Returns angle (in degrees) at point b
    """
    ax, ay = a.x, a.y
    bx, by = b.x, b.y
    cx, cy = c.x, c.y

    ab = (ax - bx, ay - by)
    cb = (cx - bx, cy - by)

    dot = ab[0]*cb[0] + ab[1]*cb[1]
    mag_ab = math.sqrt(ab[0]**2 + ab[1]**2)
    mag_cb = math.sqrt(cb[0]**2 + cb[1]**2)

    # Prevent division by zero
    if mag_ab * mag_cb == 0:
        return 0

    angle = math.acos(max(-1.0, min(1.0, dot / (mag_ab * mag_cb))))
    return math.degrees(angle)


def get_finger_angles(hand_landmarks):
    lm = hand_landmarks.landmark

    angles = []

    # Thumb
    angles.append(calculate_angle(lm[1], lm[2], lm[4]))

    # Index
    angles.append(calculate_angle(lm[5], lm[6], lm[8]))

    # Middle
    angles.append(calculate_angle(lm[9], lm[10], lm[12]))

    # Ring
    angles.append(calculate_angle(lm[13], lm[14], lm[16]))

    # Pinky
    angles.append(calculate_angle(lm[17], lm[18], lm[20]))

    return angles


def finger_angle_to_servo(angle):
    """Map a MediaPipe joint angle to a 0-180 servo angle.

    Fully extended finger (~175°) -> servo 0°.
    Fully curled  finger (~40°)  -> servo 180°.
    """
    lo, hi = FINGER_ANGLE_RANGE
    if angle <= lo:
        return 180
    if angle >= hi:
        return 0
    return int(round((hi - angle) / (hi - lo) * 180))


def fingers_to_servo_angles(finger_angles):
    """Pick the four fingers we send to the servos: index, middle, ring, pinky."""
    selected = finger_angles[1:1 + NUM_SERVOS]
    return [finger_angle_to_servo(a) for a in selected]


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


def open_arduino(port, no_arduino):
    if no_arduino:
        print("Running without Arduino (--no-arduino).")
        return None
    try:
        arduino = ArduinoServos(port=port)
        print(f"Connected to Arduino on {arduino.port}.")
        return arduino
    except Exception as exc:
        print(f"Continuing without Arduino: {exc}")
        return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Hand-tracking demo that drives four servos on an Arduino Uno."
    )
    parser.add_argument(
        "--camera", type=int, default=2,
        help="OpenCV camera index (default: 2).",
    )
    parser.add_argument(
        "--port", help="Arduino serial port (auto-detected by default).",
    )
    parser.add_argument(
        "--no-arduino", action="store_true",
        help="Skip connecting to the Arduino; just display tracking on screen.",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Slowly open and close all fingers, ignoring the camera.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    arduino = open_arduino(args.port, args.no_arduino)

    if args.demo:
        if arduino is None:
            print("--demo requires an Arduino connection.", file=sys.stderr)
            return 1
        try:
            open_close_demo(arduino)
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            arduino.close()
        return 0

    cap = cv2.VideoCapture(args.camera, cv2.CAP_AVFOUNDATION)

    send_interval = 1.0 / SERVO_SEND_HZ
    last_send = 0.0
    last_servo_angles = [90] * NUM_SERVOS

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            result = hands.process(rgb_frame)
            finger_angles = [0, 0, 0, 0, 0]
            hand_visible = False

            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    finger_angles = get_finger_angles(hand_landmarks)
                    hand_visible = True

            if hand_visible:
                servo_angles = fingers_to_servo_angles(finger_angles)
            else:
                servo_angles = last_servo_angles

            now = time.monotonic()
            if arduino is not None and now - last_send >= send_interval:
                try:
                    arduino.send_angles(servo_angles)
                    last_send = now
                except Exception as exc:
                    print(f"Serial write failed: {exc}")
            last_servo_angles = servo_angles

            cv2.putText(frame, f"Angles: {[int(a) for a in finger_angles]}", (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

            cv2.putText(frame, f"Servos: {servo_angles}", (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

            cv2.imshow("Hand Tracking", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if arduino is not None:
            arduino.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
