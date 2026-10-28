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

You do this once. After that, just open Claude Code.

## Easiest: one-command automatic setup

If you'd rather not do any of the manual steps below, run the auto-setup script.
It installs VirtualBox + Vagrant, builds a Windows VM with the sidecar already
installed and serving, saves the VM so the plugin auto-boots it, and connects
Claude Code — all in one go.

1. Download this project (ZIP from GitHub, or `git clone`).
2. In the project's `setup` folder, **double-click `install-windows.cmd`**. Click
   **Yes** at the admin prompt. That's it.
3. Wait. The first run checks your PC, installs what's needed, downloads a
   multi-GB Windows image, and sets everything up; later there's nothing to run.

What it does for you, so it "just works":

- **Preflight check** — confirms 64-bit Windows 10/11, enough RAM and free disk,
  and that CPU virtualization is enabled, with a plain-English fix if something's
  off (it stops before the big download rather than failing halfway).
- **Reuses what you already have** — if VirtualBox and/or Vagrant are already
  installed (even if not on your PATH), it detects and uses them instead of
  reinstalling; it only installs what's missing.
- **Keeps the window open** and prints exactly what to do if a step needs you.

> Heads-up: the Windows image is a community evaluation build (it re-arms its
> trial automatically). If the download source is ever unavailable, open
> `setup/Vagrantfile` and change `WINDOWS_BOX` to another public Windows box.
> This installer is new and can't be tested without a real Windows machine — if a
> step fails, copy the error and we'll fix it.

Once it finishes, skip to [§5 Everyday use](#5-everyday-use--just-open-claude-code).
The manual steps below are only if you prefer to set the VM up yourself.

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

## 4. Wire it up (once)

**Inside the VM**, from the project folder, run this one script:

```bat
setup\vm-autostart.bat
```

It installs the desktop server and makes it launch **automatically (hidden) every
time the VM starts**. You never run anything in the VM again.

**On your host PC** (not the VM), from the project folder:

```bat
setup\vm-host.bat "Exact VM Name"
```

It adds the loopback port-forward (saved permanently on the VM) and connects
Claude Code. If you installed the sidecar-desktop **plugin**, the Claude
connection is already done — this step then only adds the port-forward, which
you can also do once in VirtualBox (Settings ▸ Network ▸ Advanced ▸ Port
Forwarding: `127.0.0.1:8765 → 8765`).

That's the entire setup. From now on it's just the two steps below.

## 5. Everyday use — just open Claude Code

Once the setup above is done, the **plugin handles everything**: when you start a
Claude Code session, the plugin boots the VM (if it isn't already running) and
connects to it. You don't start the VM, run any script, or keep a window open.

Just ask Claude to use the sidecar desktop, e.g. *"Open Edge in your sidecar
desktop and sign in to my email."* It drives the **VM**, not your PC. Snap the
VirtualBox window to half your screen (Win+← / Win+→) to watch and take over when
needed (e.g. a login or 2FA, after which Claude continues in that signed-in
session).

Your real mouse, keyboard and screen stay entirely yours the whole time. (The
auto-boot comes from a plugin hook that only acts when `vm-host.bat` has saved
your VM name; it does nothing on machines without the VM.)

## Notes

- **Logins persist** in the VM between sessions (unlike Windows Sandbox), so you
  sign in to things once.
- **Security:** the server only accepts connections via the host loopback
  forward and only localhost `Host` headers; the NAT VM isn't reachable from your
  network. It can read/write files under the VM user's home folder (not your
  host's). Treat the VM's browser like any automated one — only sign in to
  accounts you're comfortable with Claude using.
- **To turn autostart off**, delete `sidecar-desktop.vbs` from the VM's
  `shell:startup` folder.
- If Claude's tools show a connection error, make sure the VM is running and that
  you ran `vm-host.bat` once (or added the port-forward in VirtualBox). The guest
  server itself needs no window open — it runs hidden in the background.
- `setup\vm-guest.bat` still exists if you ever want to run the server in a
  visible window (for debugging) instead of via autostart.
