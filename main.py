import argparse
import sys
import time

import cv2
import mediapipe as mp

from arduino import ArduinoServos, NUM_SERVOS, open_close_demo
from hand_tracking import (
    draw_landmark_indices,
    fingers_to_servo_angles,
    get_finger_angles,
    smooth_servo_angles,
)

SERVO_SEND_HZ = 30.0  # Cap servo updates so we don't saturate the serial link

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Hand-tracking demo that drives six servos on an Arduino Uno."
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

    if args.no_arduino:
        print("Running without Arduino (--no-arduino).")
        arduino = None
    else:
        try:
            arduino = ArduinoServos(port=args.port)
            print(f"Connected to Arduino on {arduino.port}.")
        except Exception as exc:
            print(f"Continuing without Arduino: {exc}")
            arduino = None

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
    smoothed_servo_angles = [0.0] * NUM_SERVOS

    try:
        while True:
            frame_ok, frame = cap.read()
            if not frame_ok:
                break

            frame = cv2.flip(frame, 1) # Flip the frame horizontally
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # MediaPipe requires RGB format

            result = hands.process(rgb_frame)
            finger_angles = [0] * NUM_SERVOS
            hand_visible = False

            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    draw_landmark_indices(frame, hand_landmarks)
                    finger_angles = get_finger_angles(hand_landmarks)
                    hand_visible = True

            if hand_visible:
                target_servo_angles = fingers_to_servo_angles(finger_angles)
            else:
                target_servo_angles = smoothed_servo_angles

            smoothed_servo_angles = smooth_servo_angles(
                smoothed_servo_angles, target_servo_angles
            )
            servo_angles = [int(round(a)) for a in smoothed_servo_angles]

            now = time.monotonic()
            if arduino is not None and now - last_send >= send_interval:
                try:
                    arduino.send_angles(servo_angles)
                    last_send = now
                except Exception as exc:
                    print(f"Serial write failed: {exc}")

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
