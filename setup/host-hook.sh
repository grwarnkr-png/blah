#!/usr/bin/env bash
# Plugin SessionStart hook (runs on the HOST, cross-platform via Git Bash on
# Windows). Makes the Windows-VM path hands-off: when Claude Code starts, it
# boots the sidecar VM (if not already running) and makes sure the loopback
# port-forward exists — so the plugin is all you touch.
#
# It does NOTHING unless setup/vm-host.bat has saved a VM name, so Docker/native
# users (and non-VirtualBox machines) are unaffected. It never blocks a session:
# every path exits 0.

NAMEFILE="$HOME/.sidecar-desktop/vmname"
[ -f "$NAMEFILE" ] || exit 0
VM="$(head -n1 "$NAMEFILE" 2>/dev/null | tr -d '\r')"
[ -n "$VM" ] || exit 0

VBM="$(command -v VBoxManage 2>/dev/null)"
if [ -z "$VBM" ]; then
  for c in "/c/Program Files/Oracle/VirtualBox/VBoxManage.exe" \
           "/c/Program Files (x86)/Oracle/VirtualBox/VBoxManage.exe" \
           "/Applications/VirtualBox.app/Contents/MacOS/VBoxManage"; do
    if [ -x "$c" ]; then VBM="$c"; break; fi
  done
fi
[ -n "$VBM" ] || exit 0

# Ensure the port-forward (best effort; only applies while the VM is powered off,
# and vm-host.bat already set it — this is just a safety net).
"$VBM" modifyvm "$VM" --natpf1 "sidecar,tcp,127.0.0.1,8765,,8765" >/dev/null 2>&1

# Boot the VM (with its window, so you can watch) if it isn't already running.
if ! "$VBM" list runningvms 2>/dev/null | grep -q "\"$VM\""; then
  "$VBM" startvm "$VM" --type separate >/dev/null 2>&1 &
fi

exit 0
