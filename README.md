# Sidecar Desktop

Give Claude Code its **own** screen, mouse and keyboard so it can drive GUI
apps (a browser, a desktop app) **while you keep using your computer**.

The whole point: Claude's cursor is *not* your cursor. It works on a separate
display that you can watch in a browser tab. Nothing it clicks or types touches
your real mouse, keyboard, or window focus — so it never fights you for control.

```
 you (untouched)                   Claude's sidecar desktop
 ┌──────────────────────┐          ┌───────────────────────────────┐
 │ your mouse, keyboard │          │ its own screen (1280x800)     │
 │ your windows         │   MCP    │ its own browser & apps        │
 │ Claude Code ─────────┼─────────▶│ mouse/keyboard it controls    │
 │ browser tab (watch) ◀┼──────────┤ viewer on localhost:6080      │
 └──────────────────────┘          └───────────────────────────────┘
```

## Quick start

### Linux

```bash
git clone https://github.com/grwarnkr-png/blah.git sidecar-desktop
cd sidecar-desktop
./setup/start.sh
```

That installs what it needs, wires the tools into Claude Code for every
session, and roots file access at your home folder. Claude gets its own display
on your machine — so it can run **your installed apps** and read **your files** —
without touching your cursor. Watch at <http://localhost:6080/vnc.html> while a
session is running.

### Windows

Double-click **`setup\start.bat`** (needs [Docker
Desktop](https://www.docker.com/products/docker-desktop/) running). Windows
can't hand Claude an independent on-screen cursor without a second login
session, so the no-conflict version runs a private **Linux** desktop in a
container that you watch at <http://localhost:6080/vnc.html>. Your real mouse
and keyboard stay yours. (Trade-off: it runs its own Linux browser/apps, not
your installed Windows programs — see [below](#windows-native-apps).)

### macOS

Same reasoning as Windows — run the Docker desktop:

```bash
docker compose up -d --build        # then open http://localhost:6080/vnc.html
claude mcp add --transport http --scope user sidecar-desktop http://127.0.0.1:8765/mcp
```

Then just ask, e.g. *"Use your sidecar desktop to open Firefox, find the latest
release notes for X and summarize them into ~/notes/x.md."*

## What Claude gets

**Desktop**

| Tool | What it does |
|---|---|
| `about` | which mode it's in, screen size, file root |
| `screenshot` | PNG of the whole screen |
| `click` | left/middle/right click; `clicks: 2` double-clicks |
| `move_mouse` | hover without clicking |
| `drag` | press, move, release |
| `scroll` | mouse wheel at a point |
| `type_text` | type into the focused window |
| `key` | key or chord: `enter`, `ctrl+l`, `ctrl+shift+t`, `alt+F4` |
| `cursor_position` | where its pointer is |
| `launch` | start a program, e.g. `firefox https://…` |
| `wait` | pause for loading, then look |

**Files** (confined to one root — your home folder by default)

| Tool | What it does |
|---|---|
| `list_dir` | list a folder under the root |
| `read_file` | read a UTF-8 text file under the root |
| `write_file` | write or append a text file under the root |

Action tools return a fresh screenshot by default; pass `screenshot: false` to
skip it and chain quick actions, then look once at the end.

## Modes

| | Isolated (Docker, or Linux `--start-xvfb`) | Native real-desktop (`--native`) |
|---|---|---|
| Claude's cursor | separate display — never touches yours | **your real cursor** (it will move while Claude works) |
| Conflicts with your use | no | yes — you share one cursor |
| Your installed apps | Linux apps in the container; your own apps in Linux `--start-xvfb` | yes, all of them |
| Recommended | **yes** | only if you specifically want Claude on your actual screen |

The Linux quick-start uses the isolated display *on your own machine*, which is
the best of both: your real files and installed apps, but an independent cursor.
`--native` (real-desktop control via `pyautogui`) exists for the rare case you
want Claude on your literal screen; it conflicts with your own input by design.

## Logins and credentials

In every mode Claude uses sessions **you** are signed into — it doesn't extract
or store your credentials. When something needs a login or 2FA, do it yourself
in the viewer window; Claude then uses the authenticated session. Don't expect
it to type passwords it wasn't given, and treat its browser like any automated
one: only sign in to accounts you're comfortable with it using.

## Configuration

Re-run `claude mcp add` with different flags to change behavior:

```bash
# scope file access to one folder instead of all of home
claude mcp add --scope user sidecar-desktop -- \
  /path/to/.venv/bin/python /path/to/sidecar/server.py \
  --start-xvfb --viewer --file-root "$HOME/work"

# turn off file tools entirely (desktop control only)
... --start-xvfb --viewer --no-files
```

Environment variables: `WIDTH`/`HEIGHT` (screen size, default 1280x800),
`SIDECAR_SETTLE_SECONDS` (delay before the post-action screenshot),
`SIDECAR_TYPE_DELAY_MS` (keystroke delay), `SIDECAR_FILE_ROOT` (default file root).

## Install it as a plugin (Docker/HTTP mode)

Instead of `claude mcp add`, you can install it as a Claude Code plugin, which
also adds a short skill telling Claude how to use the desktop:

```
/plugin marketplace add grwarnkr-png/blah
/plugin install sidecar-desktop@sidecar-desktop
```

The plugin points at the HTTP server on `127.0.0.1:8765` (the Docker mode), so
run `docker compose up -d` alongside it.

## Security notes

- Everything binds to `127.0.0.1` only — nothing on your network can reach the
  desktop or the viewer. The HTTP endpoint also rejects non-localhost `Host`
  headers (DNS-rebinding protection).
- The viewer has no password; anyone with access to your machine's localhost can
  watch or control the sidecar desktop. Set `VIEW_ONLY=1` (Docker) to make the
  viewer watch-only.
- File tools are confined to the root you choose; paths that resolve outside it
  (via `..` or symlinks) are refused. Pick a narrower `--file-root` if you don't
  want all of home reachable.

<a name="windows-native-apps"></a>
## Windows-native apps

Driving your *installed Windows programs* without conflicting with your own
cursor needs a second Windows session (a separate desktop or VM), which this
setup doesn't create. The Docker desktop covers browser and Linux-app tasks
without that complexity. If you truly need Windows-native apps under automation,
that's a bigger build — open an issue describing the use case.

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
