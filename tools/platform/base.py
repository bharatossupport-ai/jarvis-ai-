"""Same interface on every OS; each adapter implements what its OS allows."""


class DesktopAdapter:
    name = "generic"
    capabilities = set()

    def launch(self, command: str): raise NotImplementedError
    def list_windows(self) -> list: return []
    def focus_window(self, title: str): raise NotImplementedError("Not supported on this system")
    def type_text(self, window_title: str, text: str): raise NotImplementedError("Not supported on this system")
    def click_control(self, window_title: str, control_name: str): raise NotImplementedError("Not supported on this system")
    def notify(self, title: str, message: str): pass
