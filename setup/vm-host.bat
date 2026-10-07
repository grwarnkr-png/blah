@echo off
REM ===== RUN THIS ON YOUR MAIN PC (the host), not inside the VM =====
REM It forwards localhost:8765 on your PC into the VM, and connects Claude Code
REM to the sidecar running there. Pass your VM's exact name (as shown in the
REM VirtualBox window / `VBoxManage list vms`):
REM     setup\vm-host.bat "My Windows VM"
setlocal
cd /d "%~dp0\.."

if "%~1"=="" (echo Usage: vm-host.bat "Exact VM Name"  ^(see VirtualBox Manager^) & pause & exit /b 1)
set "VMNAME=%~1"

set "VBM=%ProgramFiles%\Oracle\VirtualBox\VBoxManage.exe"
if not exist "%VBM%" set "VBM=%ProgramFiles(x86)%\Oracle\VirtualBox\VBoxManage.exe"
if not exist "%VBM%" (echo Could not find VBoxManage.exe. Is VirtualBox installed? & pause & exit /b 1)

where claude >nul 2>&1 || (echo Claude Code is not installed on this PC. Install it, then run this again. & pause & exit /b 1)

echo.
echo ==^> Forwarding localhost:8765 on this PC into VM "%VMNAME%"
REM Works whether the VM is running or stopped; replaces any existing rule of this name.
"%VBM%" controlvm "%VMNAME%" natpf1 delete sidecar >nul 2>&1
"%VBM%" modifyvm  "%VMNAME%" --natpf1 delete sidecar >nul 2>&1
"%VBM%" controlvm "%VMNAME%" natpf1 "sidecar,tcp,127.0.0.1,8765,,8765" 2>nul || ^
"%VBM%" modifyvm  "%VMNAME%" --natpf1 "sidecar,tcp,127.0.0.1,8765,,8765" || ^
 (echo Could not add the port-forward. Make sure the VM uses a NAT adapter. & pause & exit /b 1)

echo.
echo ==^> Saving the VM name so the plugin can auto-boot it each session
if not exist "%USERPROFILE%\.sidecar-desktop" mkdir "%USERPROFILE%\.sidecar-desktop"
> "%USERPROFILE%\.sidecar-desktop\vmname" echo %VMNAME%

echo.
echo ==^> Connecting Claude Code to the VM desktop
claude mcp remove sidecar-desktop >nul 2>&1
claude mcp add --transport http --scope user sidecar-desktop http://127.0.0.1:8765/mcp

echo.
echo   Done.
echo.
echo   1) Start the VM, and inside it run  setup\vm-guest.bat  (leave it open).
echo   2) Start a new Claude Code session on this PC and ask it to use the
echo      sidecar desktop. It drives the VM, not your PC.
echo   3) Snap the VirtualBox window to half your screen to watch / take over.
echo.
pause
