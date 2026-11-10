"""JSON settings with defaults. Secrets (API keys) go to the OS keyring, never here."""
import json
from copy import deepcopy
from .paths import data_dir

DEFAULTS = {
    "provider": "embedded",            # "embedded" (built-in Hermes), "ollama" or "cloud"
    "ollama_url": "http://127.0.0.1:11434",
    "ollama_model": "gemma3:1b",       # multilingual, handles Hindi well for its size
    "cloud_base_url": "https://api.openai.com/v1",
    "cloud_model": "gpt-4o-mini",
    "request_timeout": 120,
    "max_context_messages": 20,
    "theme": "dark",
    "voice_enabled": True,
    "whisper_model": "base",           # bundled; tiny/small download on first use
    "piper_voice": "",                 # path to a .onnx Piper voice
    "mic_device": None,
    "speak_replies": False,
    "allowed_apps": {},                # {"Notepad": "notepad.exe"}
    "allowed_folders": [],             # folders ATLAS may touch
    "browser_headless": False,
    "show_3d_companion": True,
    "tray_enabled": True,
    "language": "auto",                # "auto" (match user), "hi", "en"
    "voice_language": "auto",          # Whisper: "auto", "hi", "en"
    "auto_learn": True,                # learn facts while chatting
    "auto_approve_learned": True,      # False = learned facts wait for approval
    "enabled_connectors": [],
    "embedded_model_path": "",         # empty = bundled model in the app's models folder
    "embedded_ctx": 4096,
    "webhook_url": "",
}

_PATH = data_dir() / "settings.json"


class Settings:
    def __init__(self):
        self.data = deepcopy(DEFAULTS)
        if _PATH.exists():
            try:
                self.data.update(json.loads(_PATH.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass

    def get(self, key, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def save(self):
        _PATH.write_text(json.dumps(self.data, indent=2), encoding="utf-8")


SERVICE = "JARVIS-AI"


def get_secret(name: str):
    try:
        import keyring
        return keyring.get_password(SERVICE, name)
    except Exception:
        return None


def set_secret(name: str, value: str):
    import keyring
    keyring.set_password(SERVICE, name, value)
