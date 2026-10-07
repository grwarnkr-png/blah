@echo off
REM ===== RUN THIS INSIDE THE WINDOWS VM (the guest), not on your main PC =====
REM It sets up the sidecar server in native mode and serves it over HTTP so your
REM host PC's Claude Code can drive THIS VM's desktop. The VM has its own cursor,
REM so your real mouse and keyboard are never touched.
setlocal
cd /d "%~dp0\.."

where python >nul 2>&1 || (echo Python is not installed in this VM. Get it from https://python.org ^(tick "Add python.exe to PATH"^), then run this again. & pause & exit /b 1)

echo.
echo ==^> Setting up the VM desktop agent (about a minute)
python -m venv .venv || (echo Could not create the environment. & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt pyautogui || (echo Install failed. & pause & exit /b 1)

echo.
echo ==^> Serving the desktop on port 8765 (leave this window open)
echo     Your host PC connects to it through the port-forward set by vm-host.bat.
echo.
REM Bind 0.0.0.0 so the VM's NAT port-forward can reach it; the server still only
REM accepts localhost Host headers, which is what the host's loopback forward sends.
python sidecar\server.py --native --transport http --host 0.0.0.0 --port 8765 --file-root "%USERPROFILE%"

echo.
echo (server stopped)
pause
