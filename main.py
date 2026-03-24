import cv2
import mediapipe as mp
import time
import math

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

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

    angle = math.acos(dot / (mag_ab * mag_cb))
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

def get_finger_states(hand_landmarks):
    landmarks = hand_landmarks.landmark
    finger_states = []

    if landmarks[4].x < landmarks[3].x:
        finger_states.append(1)
    else:
        finger_states.append(0)

    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]

    for tip, pip in zip(tips, pips):
        if landmarks[tip].y < landmarks[pip].y:
            finger_states.append(1)
        else:
            finger_states.append(0)

    return finger_states

# Webcam setup
# May have to change this to 0 for different computers
cap = cv2.VideoCapture(2, cv2.CAP_AVFOUNDATION)

# Main loop
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    result = hands.process(rgb_frame)

    finger_states = [0, 0, 0, 0, 0]
    finger_angles = [0, 0, 0, 0, 0]

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            finger_states = get_finger_states(hand_landmarks)
            finger_angles = get_finger_angles(hand_landmarks)

    cv2.putText(frame, f"States: {finger_states}", (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.putText(frame, f"Angles: {[int(a) for a in finger_angles]}", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    cv2.imshow("Hand Tracking", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()