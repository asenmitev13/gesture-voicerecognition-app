import math
import time
from typing import Optional

import cv2
import mediapipe as mp

from device_controller import execute_command, get_system_volume_percent


PINCH_STABILITY_FRAMES = 3
PINCH_RELEASE_FRAMES = 3

PINCH_THRESH_NORM = 0.045
PINCH_RELEASE_NORM = 0.060

UP_START_PX = 12
DOWN_START_PX = 12

UP_TRIGGER_PX = 20
DOWN_TRIGGER_PX = 20

PX_PER_STEP = 10

STATE_IDLE = "IDLE"
STATE_ARMED = "ARMED"

state = STATE_IDLE
value = 50

pinch_on_count = 0
pinch_off_count = 0

anchor_y_px: Optional[int] = None
gesture_direction: Optional[str] = None

last_light_gesture_time = 0
LIGHT_GESTURE_COOLDOWN = 1.5

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

THUMB_TIP = mp_hands.HandLandmark.THUMB_TIP
INDEX_TIP = mp_hands.HandLandmark.INDEX_FINGER_TIP
MIDDLE_TIP = mp_hands.HandLandmark.MIDDLE_FINGER_TIP
RING_TIP = mp_hands.HandLandmark.RING_FINGER_TIP
PINKY_TIP = mp_hands.HandLandmark.PINKY_TIP

INDEX_PIP = mp_hands.HandLandmark.INDEX_FINGER_PIP
MIDDLE_PIP = mp_hands.HandLandmark.MIDDLE_FINGER_PIP
RING_PIP = mp_hands.HandLandmark.RING_FINGER_PIP
PINKY_PIP = mp_hands.HandLandmark.PINKY_PIP


def clamp(v, mn, mx):
    return max(mn, min(mx, v))


def norm_dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def is_pinch(hand_landmarks) -> bool:
    thumb = hand_landmarks.landmark[THUMB_TIP]
    index = hand_landmarks.landmark[INDEX_TIP]
    return norm_dist(thumb, index) <= PINCH_THRESH_NORM


def is_pinch_released(hand_landmarks) -> bool:
    thumb = hand_landmarks.landmark[THUMB_TIP]
    index = hand_landmarks.landmark[INDEX_TIP]
    return norm_dist(thumb, index) >= PINCH_RELEASE_NORM


def enter_armed(hand_landmarks, frame_h: int) -> None:
    global state, anchor_y_px, gesture_direction, pinch_on_count, pinch_off_count
    tip = hand_landmarks.landmark[INDEX_TIP]
    anchor_y_px = int(tip.y * frame_h)
    gesture_direction = None
    pinch_on_count = 0
    pinch_off_count = 0
    state = STATE_ARMED


def reset_to_idle() -> None:
    global state, pinch_on_count, pinch_off_count, anchor_y_px, gesture_direction
    state = STATE_IDLE
    pinch_on_count = 0
    pinch_off_count = 0
    anchor_y_px = None
    gesture_direction = None


def fingers_extended(hand_landmarks) -> int:
    count = 0
    fingers = [
        (INDEX_TIP, INDEX_PIP),
        (MIDDLE_TIP, MIDDLE_PIP),
        (RING_TIP, RING_PIP),
        (PINKY_TIP, PINKY_PIP),
    ]

    for tip_idx, pip_idx in fingers:
        tip = hand_landmarks.landmark[tip_idx]
        pip = hand_landmarks.landmark[pip_idx]
        if tip.y < pip.y:
            count += 1

    return count


def detect_light_gesture(hand_landmarks):
    global last_light_gesture_time

    now = time.time()
    if now - last_light_gesture_time < LIGHT_GESTURE_COOLDOWN:
        return None

    extended = fingers_extended(hand_landmarks)

    # open palm
    if extended >= 4:
        last_light_gesture_time = now
        return "light_on"

    # fist
    if extended == 0:
        last_light_gesture_time = now
        return "light_off"

    return None


def apply_volume_step(step: int) -> None:
    global value
    if step == 0:
        return

    value = clamp(value + step, 0, 100)
    execute_command("set_volume", value, source="gesture")


def run_gesture(camera_index=0):
    global state, pinch_on_count, pinch_off_count, anchor_y_px, gesture_direction, value

    value = get_system_volume_percent()

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("[GESTURE] Cannot open camera.")
        return

    print("[GESTURE] Gesture module started.")
    print("[GESTURE] Gestures:")
    print("          Open palm -> light ON")
    print("          Fist      -> light OFF")
    print("          Pinch + move up/down -> volume control")
    print("          Press Q in camera window to quit gesture module")

    with mp_hands.Hands(
        model_complexity=0,
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as hands:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = hands.process(rgb)

            if res.multi_hand_landmarks:
                hand_lms = res.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(frame, hand_lms, mp_hands.HAND_CONNECTIONS)

                # simulated light gestures
                light_cmd = detect_light_gesture(hand_lms)
                if light_cmd is not None:
                    execute_command(light_cmd, source="gesture")

                pinch = is_pinch(hand_lms)
                released = is_pinch_released(hand_lms)

                if state == STATE_IDLE:
                    if pinch:
                        pinch_on_count += 1
                    else:
                        pinch_on_count = 0

                    if pinch_on_count >= PINCH_STABILITY_FRAMES:
                        enter_armed(hand_lms, h)

                if state == STATE_ARMED:
                    if released:
                        pinch_off_count += 1
                    else:
                        pinch_off_count = 0

                    if pinch_off_count >= PINCH_RELEASE_FRAMES:
                        reset_to_idle()
                        continue

                    tip = hand_lms.landmark[INDEX_TIP]
                    y_px = int(tip.y * h)

                    if anchor_y_px is None:
                        anchor_y_px = y_px

                    dy = y_px - anchor_y_px

                    if gesture_direction is None:
                        if dy <= -UP_START_PX:
                            gesture_direction = "UP"
                        elif dy >= DOWN_START_PX:
                            gesture_direction = "DOWN"

                    if gesture_direction == "UP":
                        up_dist = -dy
                        if up_dist >= UP_TRIGGER_PX:
                            step = int(up_dist // PX_PER_STEP)
                            if step > 0:
                                apply_volume_step(+step)
                                anchor_y_px = y_px

                    elif gesture_direction == "DOWN":
                        down_dist = dy
                        if down_dist >= DOWN_TRIGGER_PX:
                            step = int(down_dist // PX_PER_STEP)
                            if step > 0:
                                apply_volume_step(-step)
                                anchor_y_px = y_px

                cv2.putText(frame, f"Volume: {value}%", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"State: {state}", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

            else:
                reset_to_idle()

            cv2.imshow("Smart Home Control - Gestures", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    print("[GESTURE] Gesture module stopped.")