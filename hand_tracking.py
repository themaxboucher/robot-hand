import math
import cv2

from arduino import NUM_SERVOS

# Roughly the PIP-joint angle range we see from MediaPipe in practice:
# fully curled is ~40°, fully extended is ~175°.
FINGER_ANGLE_RANGE = (30.0, 175.0)
THUMB_ANGLE_RANGE = (110.0, 160.0)
BOTTOM_THUMB_ANGLE_RANGE = (15.0, 35.0)

def calculate_angle(a, b, c):
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

    # Bottom thumb
    angles.append(calculate_angle(lm[2], lm[0], lm[5]))

    # Thumb
    angles.append(calculate_angle(lm[2], lm[3], lm[4]))

    # Index
    angles.append(calculate_angle(lm[5], lm[6], lm[8]))

    # Middle
    angles.append(calculate_angle(lm[9], lm[10], lm[12]))

    # Ring
    angles.append(calculate_angle(lm[13], lm[14], lm[16]))

    # Pinky
    angles.append(calculate_angle(lm[17], lm[18], lm[20]))

    return angles


def draw_landmark_indices(frame, hand_landmarks):
    h, w = frame.shape[:2]
    for idx, lm in enumerate(hand_landmarks.landmark):
        px = int(lm.x * w)
        py = int(lm.y * h)
        cv2.putText(
            frame,
            str(idx),
            (px + 4, py - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1,
            lineType=cv2.LINE_AA,
        )


def finger_angle_to_servo(angle, angle_range=FINGER_ANGLE_RANGE):
    lo, hi = angle_range
    if angle <= lo:
        return 180
    if angle >= hi:
        return 0
    return int(round((hi - angle) / (hi - lo) * 180))


def fingers_to_servo_angles(finger_angles):
    if len(finger_angles) != NUM_SERVOS:
        raise ValueError(f"Expected {NUM_SERVOS} joint angles, got {len(finger_angles)}")

    bottom_thumb, thumb_ip = finger_angles[0], finger_angles[1]
    four_fingers = finger_angles[2:]

    return [
        180 - finger_angle_to_servo(bottom_thumb, BOTTOM_THUMB_ANGLE_RANGE),
        finger_angle_to_servo(thumb_ip, THUMB_ANGLE_RANGE),
        *[finger_angle_to_servo(a) for a in four_fingers],
    ]