# Sidecar Desktop

Give Claude Code its **own** computer — a screen, mouse, keyboard and local
files — so it can drive GUI apps and browse the web **while you keep using your
own machine**.

It runs in one of two modes you switch between per task:

- **Isolated** — Claude gets its *own* desktop with its *own* cursor. Your real
  screen, mouse and keyboard stay entirely yours; you watch it in a browser tab
  and can snap that to half your screen. (Trade-off: a fresh desktop, so it
  can't see your already-open windows.)
- **Native** — Claude drives your *real* desktop, using your actual open windows
  and installed apps. (Trade-off: one desktop means one cursor, so while it's
  clicking it shares your mouse.)

## Install

### Windows

1. **Isolated** (recommended): install [Docker
   Desktop](https://www.docker.com/products/docker-desktop/), start it, then
   double-click **`setup\start.bat`**. Watch at
   <http://localhost:6080/vnc.html> and snap it to half your screen.
2. **Native** (use your real apps/windows): double-click **`setup\native.bat`**.

### macOS

1. **Isolated:** `docker compose up -d --build`, then
   `claude mcp add --transport http --scope user sidecar-desktop http://127.0.0.1:8765/mcp`
2. **Native:** `./setup/native.sh` (macOS will ask you to grant Accessibility +
   Screen Recording permission on first run).

### Linux

Install it as a Claude Code **plugin** (needs Docker running for the isolated
desktop):

```
/plugin marketplace add grwarnkr-png/blah
/plugin install sidecar-desktop@sidecar-desktop
docker compose up -d --build
```

Or, for an independent display **without** Docker (uses your installed apps,
keeps your cursor), run the installer, which also sets up native mode:

```bash
git clone https://github.com/grwarnkr-png/blah.git sidecar-desktop
cd sidecar-desktop && ./setup/start.sh      # isolated display + viewer
./setup/native.sh                            # optional: real-desktop mode
```

After installing, start a new Claude session and just ask, e.g. *"Use your
sidecar desktop to open Firefox, find the latest release notes for X, and save a
summary to ~/notes/x.md."* Approve the `sidecar-desktop` tools when prompted, or
allowlist them so Claude can work uninterrupted.

## What it can and can't do

| | Isolated | Native |
|---|---|---|
| Your real cursor/screen | untouched — you keep all of it | shared while Claude acts |
| Your already-open windows | no (its own fresh desktop) | **yes** |
| Your installed apps | Linux apps (Docker); your own apps on Linux `--start-xvfb` | **yes, all of them** |
| Your files | yes (rooted at home) | yes (rooted at home) |
| Watch in a browser | yes, localhost:6080 | — (it's your own screen) |

**On Windows/macOS there is no mode that both uses your live windows *and*
leaves your cursor alone** — those OSes give one cursor per login, and an
independent second cursor sharing your real windows is Linux/X11-only. Pick
isolated when you want zero conflict, native when you want Claude in your actual
apps.

## Tools Claude gets

**Desktop:** `about`, `screenshot`, `click`, `move_mouse`, `drag`, `scroll`,
`type_text`, `key`, `cursor_position`, `launch` (start a program), `wait`.

**Files** (confined to one root, your home by default): `list_dir`, `read_file`,
`write_file`.

Action tools return a fresh screenshot by default; pass `screenshot: false` to
chain quick actions and look once at the end. Screenshots are downscaled to a
compact JPEG (when Pillow is installed) to keep them fast and cheap.

## Keys

Friendly names work: `enter`, `esc`, `tab`, `ctrl+l`, `ctrl+shift+t`, `alt+F4`,
and letters/function keys directly.

## Logins and credentials

In every mode Claude uses sessions **you** are signed into — it doesn't extract
or store credentials. When a task hits a login or 2FA, do it yourself (in the
viewer for isolated mode, or on your screen for native), and Claude continues in
the authenticated session. Don't expect it to type passwords it wasn't given,
and treat its browser like any automated one.

## Configuration

Re-run `claude mcp add` with different flags to change behavior:

```bash
# scope file access to one folder instead of all of home
... --start-xvfb --viewer --file-root "$HOME/work"
# turn file tools off entirely (desktop control only)
... --start-xvfb --viewer --no-files
```

Environment variables: `WIDTH`/`HEIGHT` (screen size, default 1280x800),
`SIDECAR_MAX_WIDTH` (screenshot downscale target, default 1366),
`SIDECAR_SETTLE_SECONDS`, `SIDECAR_TYPE_DELAY_MS`, `SIDECAR_FILE_ROOT`.

## Security notes

- Everything binds to `127.0.0.1` only — nothing on your network can reach the
  desktop or viewer. The HTTP endpoint rejects non-localhost `Host` headers.
- The viewer has no password; anyone on your machine's localhost can watch or
  control the isolated desktop. Set `VIEW_ONLY=1` (Docker) for watch-only.
- File tools are confined to the chosen root; paths resolving outside it (via
  `..` or symlinks) are refused. Use a narrower `--file-root` to limit reach.

<a name="windows-native-apps"></a>
## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest
sudo apt install xvfb xdotool xterm x11vnc novnc python3-websockify fluxbox
pytest -q
```

The end-to-end test starts the server over stdio with its own Xvfb, lists the
tools, opens xterm, clicks it, types a command, checks the command ran, and
verifies file access is confined to its root.
