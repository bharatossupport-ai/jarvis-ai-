@echo off
REM Run on Windows 11 with Python 3.12 (64-bit) and Inno Setup 6 (https://jrsoftware.org/isdl.php)
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
REM Download the built-in AI, speech and voice models (~2.3 GB, once)
python packaging\fetch_models.py
pyinstaller --noconfirm packaging\jarvis.spec
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
%ISCC% installer\jarvis.iss
echo.
echo Done: Output\JARVIS-AI-Setup.exe + JARVIS-AI-Setup-1.bin (keep both in the same folder)
pause
