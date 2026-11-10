"""Linux: AT-SPI for accessible controls, wmctrl/xdotool for windows.
Full control works on X11. Wayland blocks apps from controlling other windows,
so on Wayland only launching apps and listing (where supported) are available."""
import os
import shutil
import subprocess
from .base import DesktopAdapter


def session_type():
    return os.environ.get("XDG_SESSION_TYPE", "x11" if os.environ.get("DISPLAY") else "unknown").lower()


class LinuxAdapter(DesktopAdapter):
    name = "linux"

    def __init__(self):
        self.session = session_type()
        caps = {"launch"}
        if self.session == "x11":
            if shutil.which("wmctrl"):
                caps |= {"list_windows", "focus"}
            if shutil.which("xdotool"):
                caps |= {"type"}
            try:
                import pyatspi  # noqa: F401
                caps |= {"click"}
            except ImportError:
                pass
        self.capabilities = caps

    def _need(self, cap, hint):
        if cap not in self.capabilities:
            raise RuntimeError(f"Not available in this {self.session} session. {hint}")

    def launch(self, command):
        subprocess.Popen(command.split() if " " in command else [command],
                         start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Launched {command}"

    def list_windows(self):
        self._need("list_windows", "Use an X11 session and install wmctrl.")
        out = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True).stdout
        return [line.split(None, 3)[-1] for line in out.splitlines() if line.strip()]

    def focus_window(self, title):
        self._need("focus", "Use an X11 session and install wmctrl.")
        subprocess.run(["wmctrl", "-a", title], check=True)
        return f"Focused {title}"

    def type_text(self, window_title, text):
        self._need("type", "Use an X11 session and install xdotool.")
        self.focus_window(window_title)
        subprocess.run(["xdotool", "type", "--delay", "20", text], check=True)
        return f"Typed {len(text)} characters into {window_title}"

    def click_control(self, window_title, control_name):
        self._need("click", "Use an X11 session and install python3-pyatspi.")
        import pyatspi
        desktop = pyatspi.Registry.getDesktop(0)
        for app in desktop:
            for win in app or []:
                if win and window_title.lower() in (win.name or "").lower():
                    node = pyatspi.findDescendant(win, lambda n: n and n.name == control_name)
                    if node:
                        node.queryAction().doAction(0)
                        return f"Clicked '{control_name}' in {win.name}"
        raise RuntimeError(f"Control '{control_name}' not found in '{window_title}'")

    def notify(self, title, message):
        if shutil.which("notify-send"):
            subprocess.Popen(["notify-send", title, message])
