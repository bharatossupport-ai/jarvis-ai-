# PyInstaller spec — build on the OS you are targeting:  pyinstaller packaging/jarvis.spec
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs
root = SPECPATH + "/.."
import os
datas = [(root + "/assets", "assets")]
if os.path.isdir(root + "/models"):
    datas.append((root + "/models", "models"))   # built-in Hermes + Whisper + Piper voices
binaries = collect_dynamic_libs("llama_cpp")
datas += collect_data_files("llama_cpp")
pkgs = ["faster_whisper", "piper"]
if not sys.platform.startswith("win"):
    pkgs.append("playwright")   # Linux bundles Chromium; Windows uses the built-in Edge
for pkg in pkgs:
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass
hidden = collect_submodules("apscheduler") + ["keyring.backends", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets"]
if sys.platform.startswith("win"):
    hidden += ["pywinauto", "comtypes"]

a = Analysis([root + "/app.py"], pathex=[root], datas=datas, binaries=binaries, hiddenimports=hidden + ["llama_cpp"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="JARVIS-AI", console=False,
          icon=root + ("/assets/jarvis.ico" if sys.platform.startswith("win") else "/assets/jarvis.png"))
coll = COLLECT(exe, a.binaries, a.datas, name="JARVIS-AI")
