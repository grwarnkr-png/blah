@echo off
REM Native mode for Windows: Claude drives your REAL desktop and uses your
REM actual open windows and installed apps. While it acts, it shares your one
REM mouse cursor (there is only one Windows desktop). For the no-conflict
REM isolated desktop instead, use start.bat.
setlocal
cd /d "%~dp0\.."

where python >nul 2>&1 || (echo Python is not installed. Get it from https://python.org ^(tick "Add python.exe to PATH"^), then run this again. & pause & exit /b 1)
where claude >nul 2>&1 || (echo Claude Code is not installed. Install it, then run this again. & pause & exit /b 1)

echo.
echo ==^> Setting up native mode ^(about a minute^)
python -m venv .venv || (echo Could not create the environment. & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt pyautogui || (echo Install failed. & pause & exit /b 1)

echo.
echo ==^> Connecting native mode to Claude Code
set "PY=%CD%\.venv\Scripts\python.exe"
set "SRV=%CD%\sidecar\server.py"
claude mcp remove sidecar-desktop-native >nul 2>&1
claude mcp add --scope user sidecar-desktop-native -- "%PY%" "%SRV%" --native

echo.
echo   Native mode installed as 'sidecar-desktop-native'.
echo.
echo   Claude can now use THIS PC's real desktop - your open windows and your
echo   installed apps - and read/write files under your user folder.
echo.
echo   Heads up: while Claude is clicking/typing it moves your real mouse, so
echo   let it finish an action before you grab the cursor back. Start a NEW
echo   Claude session to pick up the tools.
echo.
pause
