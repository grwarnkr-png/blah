# Sidecar Desktop - one-command auto-setup for Windows.
#
# Easiest way to run it: double-click setup\install-windows.cmd.
# (That just runs this script elevated with the right execution policy.)
#
# It checks your PC is ready, installs VirtualBox + Vagrant, builds a Windows VM
# with the sidecar desktop already installed and serving, saves the VM so the
# plugin auto-boots it, and connects Claude Code. After it finishes you never run
# it again - just open Claude Code.

$ErrorActionPreference = "Stop"

# ---- keep the window open on exit, even when double-clicked -------------------
function Pause-Exit([int]$code = 0) {
  Write-Host ""
  try { Read-Host "Press Enter to close this window" | Out-Null } catch {}
  exit $code
}

# ---- re-launch elevated if we're not admin -----------------------------------
$principal = New-Object Security.Principal.WindowsPrincipal(
  [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Host "Asking for administrator rights (needed to install VirtualBox)..."
  try {
    Start-Process powershell -Verb RunAs -ArgumentList @(
      "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"")
  } catch {
    Write-Warning "Could not elevate. Right-click install-windows.cmd and choose 'Run as administrator'."
  }
  exit
}

# Give the (elevated) window a sane, readable size and title — some setups open
# it tiny/empty otherwise.
try {
  $raw = $Host.UI.RawUI
  $raw.WindowTitle = "Sidecar Desktop Setup  -  keep this window open"
  $buf = $raw.BufferSize; $buf.Width = 120; $buf.Height = 3000; $raw.BufferSize = $buf
  $win = $raw.WindowSize; $win.Width = 110; $win.Height = 38; $raw.WindowSize = $win
} catch {}

$SetupDir = Split-Path -Parent $PSCommandPath
function Have($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

function Add-ToPath($dir) {
  if ($dir -and (Test-Path $dir) -and ($env:Path -notlike "*$dir*")) {
    $env:Path = "$dir;$env:Path"
  }
}

# Find VirtualBox / Vagrant that are ALREADY installed but maybe not on PATH
# (the usual case), so we reuse them instead of installing again.
function Resolve-ExistingTools {
  if (-not (Have "VBoxManage")) {
    $cands = @("$env:ProgramFiles\Oracle\VirtualBox", "${env:ProgramFiles(x86)}\Oracle\VirtualBox")
    try {
      $reg = (Get-ItemProperty "HKLM:\SOFTWARE\Oracle\VirtualBox" -ErrorAction SilentlyContinue).InstallDir
      if ($reg) { $cands = @($reg) + $cands }
    } catch {}
    foreach ($d in $cands) {
      if ($d -and (Test-Path (Join-Path $d "VBoxManage.exe"))) { Add-ToPath $d; break }
    }
  }
  if (-not (Have "vagrant")) {
    $cands = @("$env:ProgramFiles\Vagrant\bin", "${env:ProgramFiles(x86)}\Vagrant\bin",
               "$env:ChocolateyInstall\bin")
    foreach ($d in $cands) {
      if ($d -and (Test-Path (Join-Path $d "vagrant.exe"))) { Add-ToPath $d; break }
    }
  }
}

$fail = @()   # blocking problems
$warn = @()   # non-blocking heads-ups

Resolve-ExistingTools

Write-Host "`n=============================================="
Write-Host "  Sidecar Desktop - setup for Windows"
Write-Host "==============================================`n"
Write-Host "==> Checking your PC..."

try {
  # --- 64-bit Windows ---------------------------------------------------------
  if (-not [Environment]::Is64BitOperatingSystem) {
    $fail += "This needs 64-bit Windows."
  }

  # --- Windows 10/11 ----------------------------------------------------------
  $os = Get-CimInstance Win32_OperatingSystem
  if ([version]$os.Version -lt [version]"10.0") {
    $fail += "This needs Windows 10 or 11 (found $($os.Caption))."
  }

  # --- RAM --------------------------------------------------------------------
  $ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
  if ($ramGB -lt 6) {
    $fail += "Only $ramGB GB RAM. The VM needs ~4 GB; you want at least 6-8 GB total."
  } elseif ($ramGB -lt 8) {
    $warn += "$ramGB GB RAM is a bit low; the VM uses 4 GB, so things may feel tight."
  }

  # --- Free disk on the system drive -----------------------------------------
  $sys = $env:SystemDrive.TrimEnd(":")
  $freeGB = [math]::Round((Get-PSDrive -Name $sys).Free / 1GB, 1)
  if ($freeGB -lt 30) {
    $fail += "Only $freeGB GB free on $($env:SystemDrive). Need ~30 GB for the Windows image + VM."
  } elseif ($freeGB -lt 45) {
    $warn += "$freeGB GB free on $($env:SystemDrive); 45 GB+ is more comfortable."
  }

  # --- CPU virtualization (VT-x/AMD-V) ----------------------------------------
  $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
  if ($cpu.VirtualizationFirmwareEnabled -eq $false) {
    $fail += "CPU virtualization is OFF in your BIOS/UEFI. Enable 'Intel VT-x' / 'AMD-V' " +
             "(often under CPU or Security settings), save, reboot, then run this again."
  }

  # --- Hyper-V / WSL2 / Core Isolation grabbing the hypervisor ----------------
  if ((Get-CimInstance Win32_ComputerSystem).HypervisorPresent -eq $true) {
    $warn += "A Windows hypervisor (Hyper-V, WSL2, or Core Isolation / Memory Integrity) is " +
             "active. VirtualBox still runs but can be slow. If the VM is unusably slow, turn off " +
             "'Core Isolation > Memory Integrity' in Windows Security and reboot."
  }

  # --- winget (only needed if something still has to be installed) ------------
  $needInstall = (-not (Have "VBoxManage")) -or (-not (Have "vagrant"))
  if ($needInstall -and -not (Have "winget")) {
    $fail += "winget isn't available, and VirtualBox and/or Vagrant aren't installed yet. Open the " +
             "Microsoft Store, update 'App Installer', then run this again. (Or install VirtualBox " +
             "and Vagrant yourself and re-run - this script will detect and reuse them.)"
  }
} catch {
  $warn += "Couldn't finish every check ($($_.Exception.Message)); continuing."
}

# --- report preflight ---------------------------------------------------------
Write-Host ("   RAM: {0} GB   Free disk: {1} GB" -f $ramGB, $freeGB)
foreach ($w in $warn) { Write-Warning $w }
if ($fail.Count -gt 0) {
  Write-Host "`nCan't continue yet - please fix:`n" -ForegroundColor Red
  foreach ($f in $fail) { Write-Host "  - $f" -ForegroundColor Red }
  Pause-Exit 1
}
Write-Host "   Looks good.`n"

# ---- install VirtualBox + Vagrant --------------------------------------------
function Ensure-WingetPackage($id, $exeToCheck, $nice) {
  if (Have $exeToCheck) { Write-Host "   $nice already installed."; return }
  Write-Host "   installing $nice (this can take a few minutes)..."
  winget install -e --id $id --accept-source-agreements --accept-package-agreements --silent
  if ($LASTEXITCODE -ne 0) {
    throw "Installing $nice failed (winget exit $LASTEXITCODE). Try installing it manually, then re-run."
  }
}

try {
  Write-Host "==> Installing VirtualBox and Vagrant..."
  Ensure-WingetPackage "Oracle.VirtualBox" "VBoxManage" "VirtualBox"
  Ensure-WingetPackage "Hashicorp.Vagrant" "vagrant" "Vagrant"

  # Refresh PATH for this process so the new tools are found.
  $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
              [Environment]::GetEnvironmentVariable("Path","User")

  if (-not (Have "vagrant")) {
    Write-Host "`nVagrant was installed but isn't on PATH in this window yet." -ForegroundColor Yellow
    Write-Host "Close this window and run the installer one more time to finish." -ForegroundColor Yellow
    Pause-Exit 0
  }

  Write-Host "`n==> Building the Windows VM and installing the sidecar."
  Write-Host "    The first run downloads a multi-GB Windows image - leave it running."
  Push-Location $SetupDir
  try {
    vagrant up
    if ($LASTEXITCODE -ne 0) {
      throw "The VM build didn't finish cleanly (vagrant exit $LASTEXITCODE). Re-running usually continues where it left off; if it keeps failing, copy the messages above."
    }
  } finally {
    Pop-Location
  }

  Write-Host "`n==> Saving the VM so the plugin auto-boots it"
  $idFile = Join-Path $SetupDir ".vagrant\machines\default\virtualbox\id"
  if (Test-Path $idFile) {
    $vmId = (Get-Content $idFile -Raw).Trim()
    $dir = Join-Path $env:USERPROFILE ".sidecar-desktop"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Set-Content -Path (Join-Path $dir "vmname") -Value $vmId -Encoding ASCII
    Write-Host "   saved."
  } else {
    Write-Warning "   couldn't find the VM id; it still works via 'vagrant up', just not auto-boot."
  }

  Write-Host "`n==> Connecting Claude Code"
  if (Have "claude") {
    claude mcp remove sidecar-desktop *> $null
    claude mcp add --transport http --scope user sidecar-desktop http://127.0.0.1:8765/mcp
  } else {
    Write-Warning "   'claude' CLI not found. If you installed the sidecar-desktop plugin, the"
    Write-Warning "   connection is already set. Otherwise run, after installing Claude Code:"
    Write-Warning "     claude mcp add --transport http --scope user sidecar-desktop http://127.0.0.1:8765/mcp"
  }

  Write-Host "`n=============================================="  -ForegroundColor Green
  Write-Host "  All set!" -ForegroundColor Green
  Write-Host "==============================================`n" -ForegroundColor Green
  Write-Host "Open a new Claude Code session and ask it to use the sidecar desktop."
  Write-Host "The VM window is Claude's screen - snap it to half your display to watch."
  Write-Host "You won't need to run this again."
  Pause-Exit 0
}
catch {
  Write-Host "`nSomething went wrong:`n" -ForegroundColor Red
  Write-Host "  $($_.Exception.Message)`n" -ForegroundColor Red
  Write-Host "Copy the messages above and send them over - most first-run issues are a quick fix."
  Pause-Exit 1
}
