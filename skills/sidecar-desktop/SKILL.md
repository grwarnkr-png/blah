---
description: Use your own private desktop (the sidecar-desktop MCP tools) to operate GUI apps, websites or anything that needs a screen, mouse and keyboard, without touching the user's real cursor. Use when a task needs a browser or desktop app rather than files and shell commands.
---

You have a private virtual desktop via the `sidecar-desktop` MCP tools. It is a
separate screen: your clicks and keystrokes never reach the user's own desktop,
so they can keep working while you do.

- Start with `screenshot`. Coordinates are pixels in that image, origin top-left.
- Open apps with `launch` (for example `firefox https://example.com`, `xterm`).
- Action tools (`click`, `type_text`, `key`, `scroll`, `drag`) return a fresh
  screenshot by default. When chaining several quick actions, pass
  `screenshot: false` on all but the last to save time and context.
- Keys use xdotool names: `Return`, `Escape`, `Tab`, `ctrl+l`, `ctrl+shift+t`.
- If a page is still loading, use `wait` rather than clicking blindly.
- If the tools are missing or return connection errors, the desktop is not
  running: tell the user to start it with `docker compose up -d` in the
  sidecar-desktop repo, then watch at http://localhost:6080/vnc.html.
- The user can watch and take over at http://localhost:6080/vnc.html. Ask them
  to step in there for logins, CAPTCHAs, or anything needing their credentials;
  never type passwords you were not given for this purpose.
