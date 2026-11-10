"""Per-OS locations for data, logs and models."""
import os
import sys
from pathlib import Path

APP_NAME = "JARVIS-AI"
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")


def data_dir() -> Path:
    if IS_WINDOWS:
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    p = base / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def sub(name: str) -> Path:
    p = data_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def resource(rel: str) -> Path:
    """Locate bundled assets both from source and inside a PyInstaller build."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel
