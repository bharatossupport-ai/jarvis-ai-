#!/usr/bin/env bash
# Run on Ubuntu 22.04+/Debian 12+ (x86_64). Produces dist/JARVIS-AI and an AppImage if appimagetool is present.
set -e
sudo apt-get install -y python3-venv libportaudio2 libxcb-cursor0 wmctrl xdotool python3-pyatspi libnotify-bin || true
python3 -m venv --system-site-packages .venv   # system site-packages gives access to pyatspi
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install --with-deps chromium
pyinstaller --noconfirm packaging/jarvis.spec
mkdir -p AppDir/usr/bin && cp -r dist/JARVIS-AI/* AppDir/usr/bin/
cp assets/jarvis.png AppDir/jarvis.png
cat > AppDir/jarvis.desktop <<D
[Desktop Entry]
Name=JARVIS AI
Exec=JARVIS-AI
Icon=jarvis
Type=Application
Categories=Utility;
D
printf '#!/bin/sh\nexec "$(dirname "$0")/usr/bin/JARVIS-AI" "$@"\n' > AppDir/AppRun && chmod +x AppDir/AppRun
if command -v appimagetool >/dev/null; then appimagetool AppDir JARVIS-AI-x86_64.AppImage; fi
echo "Built: dist/JARVIS-AI/JARVIS-AI"
