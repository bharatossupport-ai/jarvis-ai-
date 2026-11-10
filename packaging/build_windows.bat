@echo off
REM Run on Windows 11 with Python 3.12 (64-bit) and Inno Setup 6 (https://jrsoftware.org/isdl.php)
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
REM Bundle Chromium inside the app so the browser tools work offline after install
set PLAYWRIGHT_BROWSERS_PATH=0
python -m playwright install chromium
pyinstaller --noconfirm packaging\jarvis.spec
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
%ISCC% installer\jarvis.iss
echo.
echo Done: Output\JARVIS-AI-Setup.exe
pause
