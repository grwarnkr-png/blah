# Troubleshooting (Windows)

## Double-clicking `install-windows.cmd` does nothing / flashes / won't run

Work down this list — the first few are by far the most common.

1. **Extract the ZIP first.** If you downloaded the project as a ZIP, you must
   **unzip it** (right-click the ZIP ▸ *Extract All*) and run the file from the
   extracted folder. Double-clicking a file *inside* the ZIP preview won't run
   it.

2. **Unblock the file.** Files from the internet are blocked by Windows.
   Right-click `install-windows.cmd` ▸ **Properties** ▸ tick **Unblock** (bottom
   right) ▸ **OK**. Then double-click again. If you see a blue *"Windows
   protected your PC"* box, click **More info ▸ Run anyway**.

3. **Say Yes to the admin prompt.** The window may flash and then a **User
   Account Control** prompt appears (possibly behind other windows) — click
   **Yes**. A new window opens and does the work.

4. **Run it from a terminal so you can see any error.** Open the extracted
   folder, type `cmd` in the address bar, and press Enter — a command window
   opens in that folder. Then run:
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File setup\auto-setup.ps1
   ```
   Whatever it prints is what to send us.

5. **Old download with wrong line endings.** Early versions of these scripts had
   Unix line endings that break on double-click. If you downloaded before this
   was fixed, re-download the project fresh.

## "winget isn't available"

Open the **Microsoft Store**, search **App Installer**, and update it (that
provides `winget`). Then run the installer again. Alternatively, install
[VirtualBox](https://www.virtualbox.org) and
[Vagrant](https://developer.hashicorp.com/vagrant/install) yourself — the
installer detects and reuses them.

## "CPU virtualization is OFF in your BIOS/UEFI"

The VM can't run until virtualization is enabled:

1. Reboot and enter BIOS/UEFI (usually **Del**, **F2**, **F10**, or **Esc**
   during startup — your PC shows which).
2. Find **Intel VT-x** / **Intel Virtualization Technology**, or **AMD-V** /
   **SVM Mode** (often under *Advanced*, *CPU*, or *Security*). Set it
   **Enabled**.
3. Save and exit, let Windows boot, then run the installer again.

## The VM is extremely slow

A Windows hypervisor is competing with VirtualBox. Turn off **Core Isolation ▸
Memory Integrity** (Windows Security ▸ Device security), and if you don't use
them, **Hyper-V** / **Virtual Machine Platform** / **Windows Subsystem for
Linux** (Control Panel ▸ *Turn Windows features on or off*). Reboot and retry.

## "Vagrant was installed but isn't on PATH yet"

winget installed Vagrant but this window hasn't picked it up. Just close the
window and double-click `install-windows.cmd` again — the second run finishes.

## The VM build (`vagrant up`) failed partway

Re-run `install-windows.cmd` — Vagrant continues from where it left off and
re-tries the step that failed. If it keeps failing on the download, the Windows
box source may be temporarily down; open `setup/Vagrantfile` and set
`WINDOWS_BOX` to another public Windows box from
<https://portal.cloud.hashicorp.com/vagrant/discover?query=windows>.

## Claude's tools show "ECONNREFUSED" / can't connect

The VM isn't serving yet. Make sure the VM is running (its window is open), give
it a minute after boot for the server to start, and confirm the port-forward
exists (VirtualBox ▸ VM ▸ Settings ▸ Network ▸ Advanced ▸ Port Forwarding should
list `127.0.0.1:8765 → 8765`). Opening a new Claude Code session re-runs the
auto-boot step.

## Still stuck

Copy everything the installer printed (step 4 above runs it so you can see it)
and send it over — first-run issues are usually a one-line fix.
