"""Windows 11: Windows UI Automation via pywinauto (accessible controls, not blind clicks)."""
import subprocess
from .base import DesktopAdapter


class WindowsAdapter(DesktopAdapter):
    name = "windows"
    capabilities = {"launch", "list_windows", "focus", "type", "click"}

    def _desktop(self):
        from pywinauto import Desktop
        return Desktop(backend="uia")

    def launch(self, command):
        subprocess.Popen(command, shell=False)
        return f"Launched {command}"

    def list_windows(self):
        return [w.window_text() for w in self._desktop().windows() if w.window_text()]

    def _find(self, title):
        return self._desktop().window(title_re=f".*{title}.*")

    def focus_window(self, title):
        w = self._find(title)
        w.set_focus()
        return f"Focused {w.window_text()}"

    def type_text(self, window_title, text):
        w = self._find(window_title)
        w.set_focus()
        w.type_keys(text, with_spaces=True, pause=0.02)
        return f"Typed {len(text)} characters into {w.window_text()}"

    def click_control(self, window_title, control_name):
        w = self._find(window_title)
        ctrl = w.child_window(title=control_name)
        ctrl.click_input()
        return f"Clicked '{control_name}' in {w.window_text()}"
