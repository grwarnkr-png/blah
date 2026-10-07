# Claude's own Windows desktop (Windows Home, via a local VM)

This gives Claude a **real, independent Windows desktop** on your own PC: its
own cursor, your Windows apps, and no fighting your mouse — because it all
happens inside a virtual machine you watch in a window. Works on Windows Home
(no Pro features needed).

```
 your PC (host)                         the VM (Claude's desktop)
 ┌────────────────────────┐             ┌──────────────────────────────┐
 │ you, your mouse/keys   │             │ Windows, its own cursor       │
 │ your apps              │  loopback   │ your Windows apps run here     │
 │ Claude Code ───────────┼── :8765 ───▶│ sidecar server (native mode)  │
 │ VirtualBox window ◀────┼─────────────┤ you watch / take over here    │
 └────────────────────────┘             └──────────────────────────────┘
```

You do this once. After that, starting the VM + one script is all it takes.

## 1. Install VirtualBox (free)

Download and install Oracle VirtualBox from <https://www.virtualbox.org>.

## 2. Create a Windows VM

You need a Windows installation for the VM. Two easy options:

- **Microsoft's free evaluation image** — Microsoft publishes ready-made Windows
  VM images for testing at
  <https://developer.microsoft.com/windows/downloads/virtual-machines/>. Import
  the `.ova` into VirtualBox (File ▸ Import Appliance). Simplest; the eval
  copy expires after a while but is fine to try this out.
- **Your own Windows ISO** — download the Windows 11 ISO from Microsoft, create a
  new VM in VirtualBox, and install it. Use a spare/valid license.

Give the VM ~4 GB RAM and leave its network adapter on the default **NAT**
(Settings ▸ Network ▸ Adapter 1 ▸ Attached to: NAT). Note the VM's exact name
in the VirtualBox Manager list — you'll pass it to the host script.

## 3. Put this project inside the VM

In the VM, install:

- **Python** from <https://python.org> — tick **"Add python.exe to PATH"**.
- This project: download the repo as a ZIP from GitHub and unzip it, or install
  git and clone it.

(You don't need Claude Code inside the VM — Claude runs on your host and
connects in.)

## 4. Wire it up

**On your host PC** (not the VM), from the project folder:

```bat
setup\vm-host.bat "Exact VM Name"
```

That forwards `localhost:8765` on your PC into the VM and points Claude Code at
it.

**Inside the VM**, from the project folder:

```bat
setup\vm-guest.bat
```

Leave that window open — it's the desktop server. The first run installs its
dependencies.

## 5. Use it

1. Start a **new** Claude Code session on your host.
2. Ask it to use the sidecar desktop, e.g. *"Open Edge in your sidecar desktop
   and sign in to my email"* — it drives the **VM**, not your PC.
3. Snap the VirtualBox window to half your screen (Win+← / Win+→) so you can
   watch and take over when needed — for example to do a login or 2FA, after
   which Claude continues in that signed-in session.

Your real mouse, keyboard and screen stay entirely yours the whole time.

## Notes

- **Logins persist** in the VM between sessions (unlike Windows Sandbox), so you
  sign in to things once.
- **Security:** the server only accepts connections via the host loopback
  forward and only localhost `Host` headers; the NAT VM isn't reachable from your
  network. It can read/write files under the VM user's home folder (not your
  host's). Treat the VM's browser like any automated one — only sign in to
  accounts you're comfortable with Claude using.
- **Autostart (optional):** to skip step 4's guest command each boot, put a
  shortcut to `setup\vm-guest.bat` in the VM's `shell:startup` folder.
- If Claude's tools show a connection error, make sure the VM is running,
  `vm-guest.bat` is still open in it, and you ran `vm-host.bat` with the correct
  VM name.
