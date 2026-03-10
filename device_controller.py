from ctypes import cast, POINTER
from typing import Optional

from pynput.keyboard import Controller, Key
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

keyboard = Controller()

light_state = False

# pycaw setup
device = AudioUtilities.GetSpeakers()
volume_api = cast(device.EndpointVolume, POINTER(IAudioEndpointVolume))


def clamp(v, mn, mx):
    return max(mn, min(mx, v))


def get_system_volume_percent() -> int:
    try:
        current = volume_api.GetMasterVolumeLevelScalar()
        return int(round(current * 100))
    except Exception:
        return 50


def set_system_volume_percent(vol_percent: int) -> None:
    vol_percent = clamp(vol_percent, 0, 100)
    volume_api.SetMasterVolumeLevelScalar(vol_percent / 100.0, None)
    print(f"[DEVICE] Volume set to {vol_percent}%")


def volume_up_steps(steps=3):
    for _ in range(steps):
        keyboard.press(Key.media_volume_up)
        keyboard.release(Key.media_volume_up)
    print(f"[DEVICE] Volume up by {steps} step(s)")


def volume_down_steps(steps=3):
    for _ in range(steps):
        keyboard.press(Key.media_volume_down)
        keyboard.release(Key.media_volume_down)
    print(f"[DEVICE] Volume down by {steps} step(s)")


def volume_mute():
    keyboard.press(Key.media_volume_mute)
    keyboard.release(Key.media_volume_mute)
    print("[DEVICE] Volume muted")


def light_on():
    global light_state
    light_state = True
    print("[DEVICE] Simulated light: ON")


def light_off():
    global light_state
    light_state = False
    print("[DEVICE] Simulated light: OFF")


def execute_command(action: str, value: Optional[int] = None, source: str = "unknown"):
    print(f"[{source.upper()}] Command received: {action}, value={value}")

    if action == "light_on":
        light_on()

    elif action == "light_off":
        light_off()

    elif action == "volume_up":
        volume_up_steps(value if value is not None else 3)

    elif action == "volume_down":
        volume_down_steps(value if value is not None else 3)

    elif action == "mute":
        volume_mute()

    elif action == "set_volume":
        if value is not None:
            set_system_volume_percent(value)

    else:
        print(f"[SYSTEM] Unknown command: {action}")