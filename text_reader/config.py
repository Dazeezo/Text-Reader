import json
import os

APPDATA = os.getenv("APPDATA", os.path.expanduser("~"))
CONFIG_DIR = os.path.join(APPDATA, "TextReader")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_HOTKEY_READ = "ctrl+alt+space"
DEFAULT_HOTKEY_STOP = "ctrl+alt+backspace"


class Config:
    def __init__(self, voice_id=None, rate=0, hotkey_read=DEFAULT_HOTKEY_READ, hotkey_stop=DEFAULT_HOTKEY_STOP):
        self.voice_id = voice_id
        self.rate = rate
        self.hotkey_read = hotkey_read
        self.hotkey_stop = hotkey_stop

    @classmethod
    def load(cls):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(
                voice_id=data.get("voice_id"),
                rate=data.get("rate", 0),
                hotkey_read=data.get("hotkey_read", DEFAULT_HOTKEY_READ),
                hotkey_stop=data.get("hotkey_stop", DEFAULT_HOTKEY_STOP),
            )
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return cls()

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "voice_id": self.voice_id,
                    "rate": self.rate,
                    "hotkey_read": self.hotkey_read,
                    "hotkey_stop": self.hotkey_stop,
                },
                f,
            )
