# Sidecar Desktop - one-command auto-setup for Windows.
#
# Right-click this file > "Run with PowerShell" (or run it from a terminal). It:
#   1. installs VirtualBox + Vagrant (via winget) if they're missing,
#   2. builds a Windows VM with the sidecar desktop already installed and serving
#      (this downloads a ~several-GB Windows image the first time - be patient),
#   3. saves the VM id so the plugin auto-boots it every session, and
#   4. connects Claude Code to it.
#
# After this finishes, you never run it again - just open Claude Code.

$ErrorActionPreference = "Stop"
$SetupDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Have($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

function Ensure-WingetPackage($id, $exeToCheck) {
  if (Have $exeToCheck) { Write-Host "  $id already present."; return }
  if (-not (Have "winget")) {
    throw "winget isn't available. Install '$id' manually (then re-run), or update Windows App Installer from the Microsoft Store."
  }
  Write-Host "  installing $id ..."
  winget install -e --id $id --accept-source-agreements --accept-package-agreements --silent
}

Write-Host "`n==> Checking VirtualBox and Vagrant"
Ensure-WingetPackage "Oracle.VirtualBox" "VBoxManage"
Ensure-WingetPackage "Hashicorp.Vagrant" "vagrant"

# winget may have updated PATH only for new processes; pull it in for this one.
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path","User")

if (-not (Have "vagrant")) {
  throw "Vagrant was installed but isn't on PATH yet. Close this window, open a new PowerShell, and run this script again."
}

Write-Host "`n==> Building the Windows VM and installing the sidecar (first run is slow)"
Push-Location $SetupDir
try {
  vagrant up
} finally {
  Pop-Location
}

Write-Host "`n==> Saving the VM id so the plugin can auto-boot it"
$idFile = Join-Path $SetupDir ".vagrant\machines\default\virtualbox\id"
if (Test-Path $idFile) {
  $vmId = (Get-Content $idFile -Raw).Trim()
  $dir = Join-Path $env:USERPROFILE ".sidecar-desktop"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  Set-Content -Path (Join-Path $dir "vmname") -Value $vmId -Encoding ASCII
  Write-Host "  saved VM id $vmId"
} else {
  Write-Warning "  couldn't find the VM id; the session hook won't auto-boot. The VM still works via 'vagrant up'."
}

Write-Host "`n==> Connecting Claude Code"
if (Have "claude") {
  claude mcp remove sidecar-desktop *> $null
  claude mcp add --transport http --scope user sidecar-desktop http://127.0.0.1:8765/mcp
} else {
  Write-Warning "  'claude' CLI not found. If you installed the plugin, the connection is already configured; otherwise run:"
  Write-Warning "    claude mcp add --transport http --scope user sidecar-desktop http://127.0.0.1:8765/mcp"
}

Write-Host "`nDone. Open a new Claude Code session and ask it to use the sidecar desktop."
Write-Host "The VM window is Claude's screen - snap it to half your display to watch.`n"
