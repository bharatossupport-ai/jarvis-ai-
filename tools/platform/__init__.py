import sys


def get_adapter():
    if sys.platform.startswith("win"):
        from .windows import WindowsAdapter
        return WindowsAdapter()
    from .linux import LinuxAdapter
    return LinuxAdapter()
