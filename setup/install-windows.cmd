@echo off
REM ====================================================================
REM  Sidecar Desktop - Windows setup.  Just double-click this file.
REM  It runs the setup (asking for admin rights once), checks your PC,
REM  installs/reuses VirtualBox + Vagrant, builds the Windows VM with the
REM  sidecar inside it, and connects Claude Code.
REM ====================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0auto-setup.ps1"
if errorlevel 1 (
  echo.
  echo Setup did not finish. See the messages above.
  pause
)
