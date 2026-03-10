import re
import speech_recognition as sr

from device_controller import execute_command


def parse_command(text: str):
    t = text.lower().strip()

    # stop
    if any(w in t for w in ["stop", "exit", "quit"]):
        return ("stop_program", None)

    # light commands
    if any(w in t for w in ["light on", "turn on light", "switch on light"]):
        return ("light_on", None)

    if any(w in t for w in ["light off", "turn off light", "switch off light"]):
        return ("light_off", None)

    # mute
    if any(w in t for w in ["mute", "silence", "quiet"]):
        return ("mute", None)

    # volume amount
    amount = 3
    m = re.search(r"(\d+)", t)
    if m:
        amount = max(1, min(int(m.group(1)), 50))

    up_words = ["volume up", "turn up", "increase", "louder", "up"]
    down_words = ["volume down", "turn down", "decrease", "lower", "down", "quieter"]

    if any(w in t for w in up_words):
        return ("volume_up", amount)

    if any(w in t for w in down_words):
        return ("volume_down", amount)

    return (None, None)


def run_voice(mic_index=1):
    recognizer = sr.Recognizer()

    try:
        mic = sr.Microphone(device_index=mic_index)
    except Exception as e:
        print("[VOICE] Microphone initialization error:", e)
        return

    print("[VOICE] Voice module started.")
    print("[VOICE] Available examples:")
    print("        'light on'")
    print("        'light off'")
    print("        'volume up 5'")
    print("        'volume down 3'")
    print("        'mute'")
    print("        'stop'")

    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
    except Exception as e:
        print("[VOICE] Could not access microphone:", e)
        return

    while True:
        try:
            with mic as source:
                audio = recognizer.listen(source, phrase_time_limit=3)

            text = recognizer.recognize_google(audio)
            print("[VOICE] Heard:", text)

            action, value = parse_command(text)

            if action == "stop_program":
                print("[VOICE] Stop command received.")
                break

            if action is not None:
                execute_command(action, value, source="voice")
            else:
                print("[VOICE] No valid command recognized.")

        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print("[VOICE] Speech recognition service error:", e)
        except Exception as e:
            print("[VOICE] Runtime error:", e)

    print("[VOICE] Voice module stopped.")