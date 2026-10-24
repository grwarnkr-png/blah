@echo off
REM Launches the sidecar desktop server in native mode, serving on port 8765.
REM Used by the autostart launchers (vm-autostart.bat and the Vagrant provisioner).
REM %~dp0 is this file's folder, so it works wherever the project lives.
"%~dp0.venv\Scripts\pythonw.exe" "%~dp0sidecar\server.py" --native --transport http --host 0.0.0.0 --port 8765 --file-root "%USERPROFILE%"
