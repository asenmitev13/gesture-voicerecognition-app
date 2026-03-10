import threading

from voice_module import run_voice
from gesture_module import run_gesture


def main():
    print("=== Smart Home Multimodal Control ===")
    print("Starting voice and gesture modules...")
    print("Voice commands can stop only the voice module with: stop")
    print("Gesture module can be stopped with: Q in the camera window")

    voice_thread = threading.Thread(target=run_voice, kwargs={"mic_index": 1}, daemon=True)
    gesture_thread = threading.Thread(target=run_gesture, kwargs={"camera_index": 0}, daemon=False)

    voice_thread.start()
    gesture_thread.start()

    gesture_thread.join()
    print("Main program finished.")


if __name__ == "__main__":
    main()