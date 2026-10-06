# Sidecar Desktop

Give Claude Code its **own** screen, mouse and keyboard so it can drive GUI
apps (a browser, a desktop app) while you keep using your computer.

Claude works on a virtual display inside a Docker container. Its clicks and
keystrokes go there and never touch your real cursor. You can watch it, or
take over for a moment, in a browser tab.

```
 your desktop (untouched)          sidecar container
 ┌──────────────────────┐          ┌───────────────────────────────┐
 │ you, your mouse,     │          │ Xvfb virtual screen 1280x800  │
 │ your apps            │          │ fluxbox · Firefox · xterm     │
 │                      │  MCP     │ xdotool (Claude's mouse/keys) │
 │ Claude Code ─────────┼─────────▶│ :8765  MCP server             │
 │ browser tab ◀────────┼──────────│ :6080  noVNC viewer           │
 └──────────────────────┘          └───────────────────────────────┘
```

Works with any Claude Code: CLI, desktop app or IDE extension, on Windows,
macOS or Linux. You only need Docker.

## Setup

1. **Start the desktop** (needs [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine):

   ```bash
   git clone https://github.com/grwarnkr-png/blah.git sidecar-desktop
   cd sidecar-desktop
   docker compose up -d --build
   ```

   It restarts with Docker, and keeps its home folder (browser logins and so
   on) in a volume.

2. **Connect Claude Code.** Pick one option.

   - **As a plugin** (adds the MCP server and a skill that tells Claude how to use it):
     ```
     /plugin marketplace add grwarnkr-png/blah
     /plugin install sidecar-desktop@sidecar-desktop
     ```
   - **Just the MCP server:**
     ```bash
     claude mcp add --transport http --scope user sidecar-desktop http://127.0.0.1:8765/mcp
     ```

3. **Watch it work** (optional): open <http://localhost:6080/vnc.html> and
   press Connect. You can click in there to help, for example to log in
   somewhere. Set `VIEW_ONLY: "1"` in `docker-compose.yml` to make the viewer
   watch-only.

Then just ask, for example: *"Use your sidecar desktop to open Firefox, find
the latest release notes for X and summarize them."*

## Tools Claude gets

| Tool | What it does |
|---|---|
| `screenshot` | PNG of the whole virtual screen |
| `click` | left, middle or right click; `clicks: 2` for a double-click |
| `move_mouse` | hover without clicking |
| `drag` | press, move, release |
| `scroll` | mouse wheel at a point |
| `type_text` | type into the focused window |
| `key` | key or chord: `Return`, `ctrl+l`, `alt+F4` (friendly names like `enter` and `cmd` work too) |
| `cursor_position` | where Claude's pointer is |
| `launch` | start a program on the sidecar desktop, e.g. `firefox https://…` |
| `wait` | pause for loading, then look |

Action tools return a fresh screenshot by default (`screenshot: false` skips
it), which saves a round trip on every step.

## Native Linux mode (no Docker)

On Linux, Claude can instead use a hidden display on your own machine, which
means it can run your installed apps:

```bash
sudo apt install xvfb xdotool fluxbox   # fluxbox is optional
pip install -r requirements.txt
claude mcp add --scope user sidecar-desktop -- python3 /path/to/sidecar-desktop/sidecar/server.py --start-xvfb
```

The display (`:99` by default; change it with `--display`) lives as long as
the Claude Code session. Unlike the Docker mode, apps Claude launches here run
as **you**, with your files.

## Why Docker on Windows and macOS?

Windows and macOS give each logged-in session a single real cursor and
keyboard focus. A second, independent one for Claude needs a separate
session, which means a VM or a container. Docker is the lightest way to get
that everywhere. A side benefit: whatever Claude does in its browser stays in
the container, away from your files and logged-in accounts.

## Configuration

Set these under `environment:` in `docker-compose.yml`:

| Variable | Default | |
|---|---|---|
| `WIDTH` / `HEIGHT` | `1280` / `800` | Screen size. Keep it near this size: Claude reads screenshots best around 1280x800, and larger images get downscaled. |
| `VIEW_ONLY` | `0` | `1` stops the noVNC viewer from sending input |
| `SIDECAR_SETTLE_SECONDS` | `0.5` | Delay before the automatic post-action screenshot |
| `SIDECAR_TYPE_DELAY_MS` | `12` | Delay between typed keystrokes |

## Security notes

- Both ports are published on `127.0.0.1` only, so other machines on your
  network can't reach them. The MCP endpoint also rejects requests whose
  `Host` header isn't localhost (DNS-rebinding protection).
- The VNC viewer has no password. Anyone with access to your machine's
  localhost can watch or control the sidecar desktop.
- Treat the sidecar browser like any automated browser. Only log in to
  accounts you're fine with Claude using.

## Development

```bash
pip install -r requirements.txt pytest
sudo apt install xvfb xdotool xterm
pytest -q
```

The end-to-end test starts the server over stdio with its own Xvfb, opens
xterm, clicks it, types a command and checks that the command ran.
