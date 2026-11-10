"""ORION desktop tools. Apps must be allowlisted by the user in Settings."""
import platform
import psutil
from security.policy import Risk
from .platform import get_adapter
from .registry import tool, list_tasks_impl

ADAPTER = get_adapter()
_settings = None


def configure(settings):
    global _settings
    _settings = settings


@tool("open_app", "Open an allowlisted application by its friendly name", {"name": str}, Risk.EXTERNAL,
      preview=lambda a: f"Open application: {a['name']}")
def open_app(name):
    apps = _settings.get("allowed_apps") or {}
    match = next((k for k in apps if k.lower() == name.lower()), None)
    if not match:
        raise PermissionError(f"'{name}' is not in your allowed apps. Allowed: {', '.join(apps) or 'none'}")
    return ADAPTER.launch(apps[match])


@tool("list_windows", "List open window titles", {}, Risk.READ)
def list_windows():
    return ADAPTER.list_windows()


@tool("focus_window", "Bring a window to the front", {"title": str}, Risk.EXTERNAL)
def focus_window(title):
    return ADAPTER.focus_window(title)


@tool("type_text", "Type text into a window", {"window_title": str, "text": str}, Risk.EXTERNAL,
      preview=lambda a: f"Type into '{a['window_title']}':\n{a['text']}")
def type_text(window_title, text):
    return ADAPTER.type_text(window_title, text)


@tool("click_control", "Click a named button/control in a window", {"window_title": str, "control_name": str},
      Risk.EXTERNAL, preview=lambda a: f"Click '{a['control_name']}' in '{a['window_title']}'")
def click_control(window_title, control_name):
    return ADAPTER.click_control(window_title, control_name)


@tool("system_info", "CPU, memory and disk usage", {}, Risk.LOW)
def system_info():
    vm = psutil.virtual_memory()
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "ram_used_gb": round(vm.used / 1e9, 1), "ram_total_gb": round(vm.total / 1e9, 1),
        "disk_free_gb": round(psutil.disk_usage("/").free / 1e9, 1),
        "desktop_control": sorted(ADAPTER.capabilities),
    }


@tool("list_tasks", "Recent JARVIS tasks", {}, Risk.LOW)
def list_tasks():
    return list_tasks_impl()


@tool("draft_message", "Save a draft message (never sends)", {"to": str, "subject": str, "body": str}, Risk.LOW)
def draft_message(to, subject, body):
    from storage.paths import sub
    from datetime import datetime
    p = sub("drafts") / f"draft_{datetime.now():%Y%m%d_%H%M%S}.txt"
    p.write_text(f"To: {to}\nSubject: {subject}\n\n{body}", encoding="utf-8")
    return f"Draft saved to {p}"


@tool("search_knowledge", "Search your memory and documents", {"query": str}, Risk.LOW)
def search_knowledge(query):
    from memory.store import search
    return search(query)
