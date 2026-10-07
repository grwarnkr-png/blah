@echo off
REM ===== RUN THIS ONCE INSIDE THE WINDOWS VM =====
REM Sets up the sidecar desktop server AND makes it launch automatically (hidden,
REM no window) every time the VM starts. After this, you never run anything in
REM the VM again - just boot it and use Claude on your host.
setlocal
cd /d "%~dp0\.."

where python >nul 2>&1 || (echo Python is not installed in this VM. Get it from https://python.org ^(tick "Add python.exe to PATH"^), then run this again. & pause & exit /b 1)

echo.
echo ==^> Setting up the VM desktop agent (about a minute)
python -m venv .venv || (echo Could not create the environment. & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt pyautogui || (echo Install failed. & pause & exit /b 1)

set "PYW=%CD%\.venv\Scripts\pythonw.exe"
set "SRV=%CD%\sidecar\server.py"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LAUNCHER=%STARTUP%\sidecar-desktop.vbs"

echo.
echo ==^> Installing autostart launcher
REM A tiny .vbs that runs the server with pythonw (no console window), hidden.
> "%LAUNCHER%" echo Set s = CreateObject("WScript.Shell")
>> "%LAUNCHER%" echo s.Run """%PYW%"" ""%SRV%"" --native --transport http --host 0.0.0.0 --port 8765 --file-root ""%USERPROFILE%""", 0, False

if not exist "%LAUNCHER%" (echo Could not write the autostart launcher. & pause & exit /b 1)

echo.
echo ==^> Starting it now (so you don't have to reboot the VM)
start "" "%LAUNCHER%"

echo.
echo   Done. The sidecar desktop now runs automatically whenever this VM starts.
echo.
echo   Nothing else to run in the VM. On your host PC, the plugin (or
echo   setup\vm-host.bat) connects Claude to it.
echo.
echo   To turn autostart off later, delete:
echo     %LAUNCHER%
echo.
pause
