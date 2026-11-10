# JARVIS AI — Windows 11 + Linux

One Python codebase. Build it on Windows for a `.exe`, on Linux for a Linux app.

## 1. Install the AI model (both OSes)
1. Install Ollama: https://ollama.com/download
2. Pull the default model (multilingual, good Hindi for its size, runs on 12 GB RAM):
   `ollama pull gemma3:1b`
   Better Hindi if your PC keeps up: `ollama pull gemma3:4b` or `qwen2.5:3b`, then change the model in Settings.

## 2. Run from source
Windows (PowerShell):
```
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```
Linux (Ubuntu/Debian):
```
sudo apt install python3-venv libportaudio2 libxcb-cursor0 wmctrl xdotool python3-pyatspi fonts-noto-core
python3 -m venv --system-site-packages .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install --with-deps chromium
python app.py
```

## 3. Build the app
- Windows installer: install Inno Setup 6 (https://jrsoftware.org/isdl.php), then double-click `packaging\build_windows.bat` → `Output\JARVIS-AI-Setup.exe` (Start menu + desktop shortcut, optional start with Windows, uninstaller, Ollama check)
- Linux: `./packaging/build_linux.sh` → `dist/JARVIS-AI/JARVIS-AI` (+ AppImage if appimagetool is installed)
- Both at once: push this folder to GitHub; `.github/workflows/build.yml` builds `JARVIS-AI-Setup.exe` and the Linux app; download them from the run's Artifacts.

## Features
| Page | What it does |
|---|---|
| Home | Model status, PC-control capabilities, 3D companion, recent tasks |
| Chat | Chat with auto-routing to companions (`@NOVA`, `@CODEX`…), provider switch, push-to-talk, export/delete |
| Companions | 3D companion view (Qt Quick 3D; 2D fallback on weak GPUs) + all 7 specialists |
| Memory | Everything learned: approve, edit, delete, search, add documents, export |
| Workflows | Scheduled prompts with pause/resume/delete, run now, run history |
| PC Control | Allowlisted apps and folders for ORION and ATLAS |
| Integrations | Connector SDK (weather, webhook included) |
| Activity | Full audit log |
| Voice | Mic, Whisper model, spoken language (Hindi/English/auto), Piper voice |
| Settings | Ollama/cloud, API key (OS keyring), reply language, learning, backup/restore |

## Hindi
- Type in Hindi (देवनागरी), English or Hinglish; JARVIS replies in the language you used (or force Hindi/English in Settings).
- Speak Hindi: Voice → Spoken language = Hindi or Auto, Whisper model = `small` for best accuracy.
- Hindi speech output: download a `hi_IN` Piper voice (`.onnx` + `.onnx.json`) from https://huggingface.co/rhasspy/piper-voices and pick it in Voice.

## Learning while chatting
- Say "remember that…", "yaad rakhna…" or "याद रखो…" to save something instantly; "forget…" / "भूल जाओ…" removes it.
- JARVIS also picks up lasting facts on its own after each reply (🧠 Learned: … appears in chat).
- Turn off "Use learned facts right away" in Settings if you want to approve each one.

## Safety
- The model never runs shell commands; only registered, typed tools.
- Writes, deletes, app launches, browser actions and sends ask for approval showing the exact action.
- Deletes go to a JARVIS trash folder. Emergency stop: status bar button or Ctrl+Shift+X.

## Linux note
Full window control (focus, type, click) needs an **X11** session. On Wayland, app launching works but window control is limited by the OS.

## Weak GPU / 3D problems
If the 3D view fails, JARVIS falls back to a 2D orb automatically. To force software rendering: set `JARVIS_SOFTWARE_GL=1`.

## Tests
`python -m pytest -q`
