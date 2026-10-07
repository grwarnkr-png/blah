---
description: Use your own private computer (the sidecar-desktop MCP tools) to operate GUI apps, websites, or anything needing a screen, mouse and keyboard, and to read/write local files — all on a display separate from the user's, so you never disturb their mouse or windows. Use when a task needs a browser or desktop app, or local file work outside the current project.
---

You have your own computer via the `sidecar-desktop` MCP tools: a screen you
control with mouse and keyboard, plus read/write access to files under one
allowed folder. It's a **separate display** from the user's — your cursor is not
their cursor — so they keep using their own screen, mouse and keyboard while you
work. They watch you (and can step in) in a browser tab.

Working loop:
- Start with `screenshot`, or `about` to see the mode, screen size and file root.
- Coordinates are pixels in the screenshot, origin top-left.
- Open apps with `launch` (e.g. `firefox https://example.com`, `xterm`).
- Action tools (`click`, `type_text`, `key`, `scroll`, `drag`) return a fresh
  screenshot by default. Chain several with `screenshot: false` and look once at
  the end — this is faster and uses far less context.
- Keys use friendly names: `enter`, `esc`, `tab`, `ctrl+l`, `ctrl+shift+t`, `alt+F4`.
- Use `wait` while pages load rather than clicking blindly.

Files: `list_dir`, `read_file`, `write_file`, all confined to the allowed root
(paths outside it are refused). Use these for local file work.

Logins and credentials: you use sessions the user is already signed into. When a
task hits a login or 2FA, ask the user to do it in the viewer window, then
continue in the authenticated session. Don't type passwords you weren't given.

If the tools are missing or error on connect, the desktop didn't start. On
Linux the user may need to install system tools once (the server prints the
exact command); on Windows/macOS they run the Docker desktop. The user is
prompted to approve these tools the first time — tell them they can approve
once, or allowlist `sidecar-desktop` tools, so you can work without repeated
prompts.
