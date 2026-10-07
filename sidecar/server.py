"""Sidecar desktop: an MCP server that gives Claude a screen, mouse, keyboard and files.

Two ways to run it:

- **Isolated** (Docker, or Linux with ``--start-xvfb``): Claude drives a *virtual*
  display that is not the one you are using, so your real cursor stays yours.
- **Native/local** (``--backend pyautogui`` or ``--native``, the default on
  Windows/macOS): Claude drives your *real* desktop and can use the apps and
  browser sessions you are already logged in to. It shares the screen with you.

Either way it can also read and write files under one allowed root (``--file-root``,
default your home directory), for local work outside a cloud checkout.
"""

from __future__ import annotations

import argparse
import atexit
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings

# Allow running as a file (`python sidecar/server.py`) as well as a module.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sidecar.files import FileAccessError, FileScope
from sidecar.input_backend import Backend, BackendError, make_backend

INSTRUCTIONS = """\
You have a desktop you can see and control (screen, mouse, keyboard), plus
read/write access to files under one allowed folder.

Desktop: take a screenshot, act, look again. Coordinates are pixels in the
screenshot (origin top-left). Action tools return a fresh screenshot unless you
pass screenshot=false, so chain quick actions with screenshot=false and look
once at the end. Open programs with `launch` (e.g. "firefox", "notepad").
Keys use friendly names: enter, esc, tab, ctrl+l, ctrl+shift+t, alt+F4.

This may be the user's REAL desktop (native mode) or a private virtual one
(isolated mode) — the `about` tool tells you which. In native mode you share
the screen and use sessions the user is already logged in to: don't type
passwords you weren't given, and for logins/2FA ask the user to do it.

Files: use list_dir / read_file / write_file for local file work. Everything is
confined to the allowed root; paths outside it are refused.
"""

mcp = MCPServer("sidecar-desktop", instructions=INSTRUCTIONS)

SETTLE_SECONDS = float(os.environ.get("SIDECAR_SETTLE_SECONDS", "0.5"))
TYPE_DELAY_MS = int(os.environ.get("SIDECAR_TYPE_DELAY_MS", "12"))
KEY_DELAY_MS = 40
# Screenshots wider than this are downscaled (keeps tokens/latency down). Claude
# still reads small UI text fine at ~1366px. Needs Pillow; without it, full PNG.
SHOT_MAX_WIDTH = int(os.environ.get("SIDECAR_MAX_WIDTH", "1366"))

# Populated in main(); the tools read these module globals.
_backend: Backend | None = None
_files: FileScope | None = None
_mode = "isolated"


class DesktopError(ToolError):
    pass


def backend() -> Backend:
    if _backend is None:  # pragma: no cover - only if a tool is called before main()
        raise DesktopError("input backend is not initialized")
    return _backend


def files() -> FileScope:
    if _files is None:
        raise DesktopError("file access is not configured")
    return _files


def _check_point(x: int, y: int) -> None:
    w, h = backend().screen_size()
    if not (0 <= x < w and 0 <= y < h):
        raise DesktopError(f"({x}, {y}) is off-screen; the screen is {w}x{h}")


def _snapshot() -> Image:
    """Capture the screen, downscaling to a compact JPEG when Pillow is available."""
    png = backend().capture_png()
    try:
        import io

        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(png))
        if img.width > SHOT_MAX_WIDTH:
            scale = SHOT_MAX_WIDTH / img.width
            img = img.resize((SHOT_MAX_WIDTH, round(img.height * scale)), PILImage.LANCZOS)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=72)
        return Image(data=buf.getvalue(), format="jpeg")
    except Exception:
        return Image(data=png, format="png")  # Pillow missing or decode failed


def _result(message: str, screenshot: bool) -> str | list:
    if not screenshot:
        return message
    time.sleep(SETTLE_SECONDS)
    return [message, _snapshot()]


@mcp.tool(structured_output=False)
def about() -> str:
    """What kind of desktop this is, its size, and where file access is rooted."""
    w, h = backend().screen_size()
    real = "your REAL desktop (shared with you)" if _mode == "native" else "a private virtual desktop"
    root = _files.root if _files else "(file access disabled)"
    return f"Mode: {_mode} — {real}. Screen: {w}x{h}. Files rooted at: {root}."


@mcp.tool(structured_output=False)
def screenshot() -> list:
    """Look at the desktop. Returns a PNG of the whole screen."""
    w, h = backend().screen_size()
    return [f"Screen is {w}x{h}.", _snapshot()]


@mcp.tool(structured_output=False)
def click(
    x: int,
    y: int,
    button: Literal["left", "middle", "right"] = "left",
    clicks: int = 1,
    screenshot: bool = True,
) -> str | list:
    """Move the mouse to (x, y) and click. clicks=2 double-clicks, 3 triple-clicks."""
    _check_point(x, y)
    if not 1 <= clicks <= 3:
        raise DesktopError("clicks must be 1, 2 or 3")
    backend().click(x, y, button, clicks)
    return _result(f"{button} x{clicks} at ({x}, {y})", screenshot)


@mcp.tool(structured_output=False)
def move_mouse(x: int, y: int, screenshot: bool = False) -> str | list:
    """Move the mouse to (x, y) without clicking (e.g. to reveal a hover menu)."""
    _check_point(x, y)
    backend().move(x, y)
    return _result(f"mouse at ({x}, {y})", screenshot)


@mcp.tool(structured_output=False)
def drag(
    start_x: int, start_y: int, end_x: int, end_y: int, screenshot: bool = True
) -> str | list:
    """Press the left button at the start point, move to the end point, release."""
    _check_point(start_x, start_y)
    _check_point(end_x, end_y)
    backend().drag(start_x, start_y, end_x, end_y)
    return _result(f"dragged ({start_x}, {start_y}) -> ({end_x}, {end_y})", screenshot)


@mcp.tool(structured_output=False)
def scroll(
    x: int,
    y: int,
    direction: Literal["up", "down", "left", "right"] = "down",
    amount: int = 3,
    screenshot: bool = True,
) -> str | list:
    """Scroll with the mouse wheel over (x, y). amount is wheel notches."""
    _check_point(x, y)
    amount = max(1, min(amount, 50))
    backend().scroll(x, y, direction, amount)
    return _result(f"scrolled {direction} {amount} at ({x}, {y})", screenshot)


@mcp.tool(structured_output=False)
def type_text(text: str, screenshot: bool = True) -> str | list:
    """Type text into whatever has keyboard focus."""
    backend().type_text(text, TYPE_DELAY_MS)
    return _result(f"typed {len(text)} characters", screenshot)


@mcp.tool(structured_output=False)
def key(combo: str, repeat: int = 1, screenshot: bool = True) -> str | list:
    """Press a key or chord, e.g. "enter", "ctrl+l", "ctrl+shift+t", "alt+F4"."""
    repeat = max(1, min(repeat, 100))
    try:
        backend().key(combo, repeat, KEY_DELAY_MS)
    except BackendError as e:
        raise DesktopError(str(e)) from e
    return _result(f"pressed {combo}" + (f" x{repeat}" if repeat > 1 else ""), screenshot)


@mcp.tool(structured_output=False)
def cursor_position() -> str:
    """Where the mouse pointer currently is."""
    x, y = backend().cursor_position()
    return f"({x}, {y})"


@mcp.tool(structured_output=False)
def launch(command: str, screenshot: bool = True) -> str | list:
    """Start a program, e.g. "firefox https://example.com" or "notepad".

    Runs detached and returns right away; screenshot after a moment if the
    window is slow to appear.
    """
    argv = shlex.split(command, posix=(os.name != "nt"))
    if not argv:
        raise DesktopError("empty command")
    if shutil.which(argv[0]) is None and not Path(argv[0]).exists():
        raise DesktopError(f"program not found: {argv[0]!r}")
    kwargs: dict = dict(
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(argv, **kwargs)
    if screenshot:
        time.sleep(1.5)
    return _result(f"launched {argv[0]}", screenshot)


@mcp.tool(structured_output=False)
def wait(seconds: float = 1.0, screenshot: bool = True) -> str | list:
    """Wait for something to load (max 30 s), then look."""
    time.sleep(max(0.0, min(seconds, 30.0)))
    return _result(f"waited {seconds}s", screenshot)


@mcp.tool(structured_output=False)
def list_dir(path: str = ".") -> str:
    """List a folder under the allowed file root. path is relative to that root."""
    try:
        return files().list_dir(path)
    except FileAccessError as e:
        raise DesktopError(str(e)) from e


@mcp.tool(structured_output=False)
def read_file(path: str) -> str:
    """Read a UTF-8 text file under the allowed file root."""
    try:
        return files().read_file(path)
    except FileAccessError as e:
        raise DesktopError(str(e)) from e


@mcp.tool(structured_output=False)
def write_file(path: str, content: str, append: bool = False) -> str:
    """Write (or append to) a text file under the allowed file root."""
    try:
        return files().write_file(path, content, append)
    except FileAccessError as e:
        raise DesktopError(str(e)) from e


_procs: list[subprocess.Popen] = []


def _spawn(argv: list[str]) -> subprocess.Popen:
    p = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _procs.append(p)
    return p


@atexit.register
def _cleanup_procs() -> None:
    for p in reversed(_procs):
        p.terminate()


def start_xvfb(display: str, width: int, height: int) -> None:
    """Start a private Xvfb (plus a window manager if one is installed).

    This is a display independent of the one you use: Claude's cursor here never
    moves your real one, so it does not conflict with your own input.
    """
    if shutil.which("Xvfb") is None:
        raise SystemExit("Xvfb is not installed (apt install xvfb xdotool)")
    _spawn(["Xvfb", display, "-screen", "0", f"{width}x{height}x24", "-nolisten", "tcp"])
    os.environ["DISPLAY"] = display
    for _ in range(50):
        if subprocess.run(["xdotool", "getmouselocation"], capture_output=True).returncode == 0:
            break
        time.sleep(0.1)
    else:
        raise SystemExit(f"Xvfb did not come up on {display}")
    for wm in ("fluxbox", "openbox", "xfwm4", "matchbox-window-manager"):
        if shutil.which(wm):
            _spawn([wm])
            break


def start_viewer(display: str, port: int) -> str | None:
    """Expose ``display`` in a browser via x11vnc + noVNC, on localhost only.

    Returns the viewer URL, or None if the tools aren't installed (non-fatal).
    """
    if shutil.which("x11vnc") is None or shutil.which("websockify") is None:
        return None
    _spawn([
        "x11vnc", "-display", display, "-localhost", "-forever", "-shared",
        "-nopw", "-quiet", "-rfbport", "5900",
    ])
    web = next(
        (d for d in ("/usr/share/novnc", "/usr/share/webapps/novnc") if Path(d).is_dir()),
        None,
    )
    argv = ["websockify"]
    if web:
        argv += ["--web", web]
    argv += [str(port), "localhost:5900"]
    _spawn(argv)
    return f"http://localhost:{port}/vnc.html"


def main() -> None:
    global _backend, _files, _mode
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--backend",
        choices=["auto", "xdotool", "pyautogui"],
        default="auto",
        help="input backend; auto picks xdotool on Linux/X11, pyautogui elsewhere",
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help="drive the real desktop (shortcut for --backend pyautogui)",
    )
    parser.add_argument(
        "--start-xvfb",
        action="store_true",
        help="start a private virtual X display for this process (isolated Linux mode)",
    )
    parser.add_argument(
        "--viewer",
        action="store_true",
        help="serve the display in a browser (x11vnc + noVNC) so you can watch; localhost only",
    )
    parser.add_argument("--viewer-port", type=int, default=6080)
    parser.add_argument("--display", default=os.environ.get("SIDECAR_DISPLAY", ":99"))
    parser.add_argument("--width", type=int, default=int(os.environ.get("WIDTH", "1280")))
    parser.add_argument("--height", type=int, default=int(os.environ.get("HEIGHT", "800")))
    parser.add_argument(
        "--file-root",
        default=os.environ.get("SIDECAR_FILE_ROOT", str(Path.home())),
        help="folder Claude may read/write under (default: your home directory)",
    )
    parser.add_argument(
        "--no-files", action="store_true", help="disable file read/write tools entirely"
    )
    args = parser.parse_args()

    if args.start_xvfb:
        start_xvfb(args.display, args.width, args.height)
    if args.viewer:
        display = os.environ.get("DISPLAY") or args.display
        url = start_viewer(display, args.viewer_port)
        if url:
            print(f"[sidecar] watch the desktop at {url}", file=sys.stderr, flush=True)
        else:
            print(
                "[sidecar] viewer not started (install x11vnc + novnc + python3-websockify)",
                file=sys.stderr,
                flush=True,
            )

    backend_kind = "pyautogui" if args.native else args.backend
    try:
        _backend = make_backend(backend_kind)
    except BackendError as e:
        raise SystemExit(f"Could not start the input backend: {e}")
    # Isolated = a virtual display not shared with the user (Xvfb we started, or
    # the container's display). Everything else drives the real, shared desktop.
    isolated = _backend.name == "xdotool" and (args.start_xvfb or _in_container())
    _mode = "isolated" if isolated else "native"

    if not args.no_files:
        try:
            _files = FileScope(args.file_root)
        except FileAccessError as e:
            raise SystemExit(f"Bad --file-root: {e}")

    if args.transport == "stdio":
        mcp.run("stdio")
    else:
        security = TransportSecuritySettings(
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"],
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"],
        )
        mcp.run("streamable-http", host=args.host, port=args.port, transport_security=security)


def _in_container() -> bool:
    return Path("/.dockerenv").exists()


if __name__ == "__main__":
    main()
