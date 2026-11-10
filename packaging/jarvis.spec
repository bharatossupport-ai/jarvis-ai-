# PyInstaller spec — build on the OS you are targeting:  pyinstaller packaging/jarvis.spec
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
root = SPECPATH + "/.."
datas = [(root + "/assets", "assets")]
for pkg in ("faster_whisper", "piper", "playwright"):  # playwright: bundled Chromium (PLAYWRIGHT_BROWSERS_PATH=0)
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass
hidden = collect_submodules("apscheduler") + ["keyring.backends", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets"]
if sys.platform.startswith("win"):
    hidden += ["pywinauto", "comtypes"]

a = Analysis([root + "/app.py"], pathex=[root], datas=datas, hiddenimports=hidden)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="JARVIS-AI", console=False,
          icon=root + ("/assets/jarvis.ico" if sys.platform.startswith("win") else "/assets/jarvis.png"))
coll = COLLECT(exe, a.binaries, a.datas, name="JARVIS-AI")
