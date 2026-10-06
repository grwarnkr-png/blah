"""Sidecar desktop: an MCP server that gives Claude its own screen, mouse and keyboard.

Everything here acts on a single X display (``$DISPLAY``), which is meant to be a
virtual one (Xvfb) that is *not* the display you are using. Claude's clicks and
keystrokes land there, so your real cursor and keyboard stay yours.

Run inside the Docker image (see ../docker) or natively on Linux with
``--start-xvfb``.
"""

from __future__ import annotations

import argparse
import atexit
import os
import shlex
import shutil
import subprocess
import time
from typing import Literal

import mss
import mss.tools
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings

INSTRUCTIONS = """\
You have your own private desktop (a virtual X11 display) with its own mouse and
keyboard. Nothing you do here moves the user's real cursor or types into their
apps, so work freely while they use their machine.

Loop: take a screenshot, act, look again. Coordinates are pixels in the
screenshot (origin top-left). Action tools return a fresh screenshot unless you
pass screenshot=false, so chain several quick actions with screenshot=false and
look once at the end. Use `launch` to open programs (e.g. "firefox", "xterm").
Keys use xdotool names: Return, Escape, Tab, BackSpace, ctrl+l, alt+F4, super.
"""

mcp = MCPServer("sidecar-desktop", instructions=INSTRUCTIONS)

# Pause before an automatic post-action screenshot so the UI has time to repaint.
SETTLE_SECONDS = float(os.environ.get("SIDECAR_SETTLE_SECONDS", "0.5"))
TYPE_DELAY_MS = int(os.environ.get("SIDECAR_TYPE_DELAY_MS", "12"))
TYPE_CHUNK = 200  # xdotool gets unreliable with very long single arguments

BUTTONS = {"left": 1, "middle": 2, "right": 3}
SCROLL_BUTTONS = {"up": 4, "down": 5, "left": 6, "right": 7}

# Friendly names Claude (or people) commonly use, mapped to xdotool keysyms.
KEY_ALIASES = {
    "enter": "Return", "return": "Return", "esc": "Escape", "escape": "Escape",
    "backspace": "BackSpace", "delete": "Delete", "del": "Delete", "tab": "Tab",
    "space": "space", "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "home": "Home", "end": "End", "pageup": "Prior", "page_up": "Prior",
    "pagedown": "Next", "page_down": "Next", "insert": "Insert",
    "control": "ctrl", "ctl": "ctrl", "cmd": "super", "win": "super",
    "windows": "super", "meta": "super", "option": "alt",
}


class DesktopError(ToolError):
    pass


def _xdotool(*args: str) -> str:
    try:
        result = subprocess.run(
            ["xdotool", *args], capture_output=True, text=True, timeout=30, check=False
        )
    except FileNotFoundError as e:
        raise DesktopError("xdotool is not installed") from e
    if result.returncode != 0:
        raise DesktopError(f"xdotool {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def screen_size() -> tuple[int, int]:
    with mss.MSS() as sct:
        mon = sct.monitors[0]
        return mon["width"], mon["height"]


def capture_png() -> bytes:
    with mss.MSS() as sct:
        shot = sct.grab(sct.monitors[0])
        return mss.tools.to_png(shot.rgb, shot.size)


def _check_point(x: int, y: int) -> None:
    w, h = screen_size()
    if not (0 <= x < w and 0 <= y < h):
        raise DesktopError(f"({x}, {y}) is off-screen; the screen is {w}x{h}")


def normalize_key(combo: str) -> str:
    """Turn 'Ctrl+Shift+T' / 'cmd+enter' style input into an xdotool chord."""
    parts = [p.strip() for p in combo.replace(" ", "").split("+") if p.strip()]
    if not parts:
        raise DesktopError("empty key combo")
    out = []
    for p in parts:
        alias = KEY_ALIASES.get(p.lower())
        if alias:
            out.append(alias)
        elif p.lower() in ("ctrl", "shift", "alt", "super"):
            out.append(p.lower())
        else:
            out.append(p)  # already a keysym such as F5, a, Return
    return "+".join(out)


def _result(message: str, screenshot: bool) -> str | list:
    if not screenshot:
        return message
    time.sleep(SETTLE_SECONDS)
    return [message, Image(data=capture_png(), format="png")]


@mcp.tool(structured_output=False)
def screenshot() -> list:
    """Look at your desktop. Returns a PNG of the whole virtual screen."""
    w, h = screen_size()
    return [f"Screen is {w}x{h}.", Image(data=capture_png(), format="png")]


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
    _xdotool("mousemove", "--sync", str(x), str(y))
    _xdotool("click", "--repeat", str(clicks), "--delay", "80", str(BUTTONS[button]))
    return _result(f"{button} x{clicks} at ({x}, {y})", screenshot)


@mcp.tool(structured_output=False)
def move_mouse(x: int, y: int, screenshot: bool = False) -> str | list:
    """Move the mouse to (x, y) without clicking (e.g. to reveal a hover menu)."""
    _check_point(x, y)
    _xdotool("mousemove", "--sync", str(x), str(y))
    return _result(f"mouse at ({x}, {y})", screenshot)


@mcp.tool(structured_output=False)
def drag(
    start_x: int, start_y: int, end_x: int, end_y: int, screenshot: bool = True
) -> str | list:
    """Press the left button at the start point, move to the end point, release."""
    _check_point(start_x, start_y)
    _check_point(end_x, end_y)
    _xdotool("mousemove", "--sync", str(start_x), str(start_y))
    _xdotool("mousedown", "1")
    try:
        # A couple of intermediate moves so apps register an actual drag.
        mid_x, mid_y = (start_x + end_x) // 2, (start_y + end_y) // 2
        _xdotool("mousemove", "--sync", str(mid_x), str(mid_y))
        _xdotool("mousemove", "--sync", str(end_x), str(end_y))
    finally:
        _xdotool("mouseup", "1")
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
    _xdotool("mousemove", "--sync", str(x), str(y))
    _xdotool("click", "--repeat", str(amount), "--delay", "30", str(SCROLL_BUTTONS[direction]))
    return _result(f"scrolled {direction} {amount} at ({x}, {y})", screenshot)


@mcp.tool(structured_output=False)
def type_text(text: str, screenshot: bool = True) -> str | list:
    """Type text into whatever has keyboard focus. Newlines press Return."""
    for i in range(0, len(text), TYPE_CHUNK):
        _xdotool("type", "--delay", str(TYPE_DELAY_MS), "--", text[i : i + TYPE_CHUNK])
    return _result(f"typed {len(text)} characters", screenshot)


@mcp.tool(structured_output=False)
def key(combo: str, repeat: int = 1, screenshot: bool = True) -> str | list:
    """Press a key or chord, e.g. "Return", "ctrl+l", "ctrl+shift+t", "alt+F4"."""
    chord = normalize_key(combo)
    repeat = max(1, min(repeat, 100))
    _xdotool("key", "--repeat", str(repeat), "--delay", "40", "--", chord)
    return _result(f"pressed {chord}" + (f" x{repeat}" if repeat > 1 else ""), screenshot)


@mcp.tool(structured_output=False)
def cursor_position() -> str:
    """Where your mouse pointer currently is."""
    out = _xdotool("getmouselocation", "--shell")
    vals = dict(line.split("=", 1) for line in out.split() if "=" in line)
    return f"({vals.get('X')}, {vals.get('Y')})"


@mcp.tool(structured_output=False)
def launch(command: str, screenshot: bool = True) -> str | list:
    """Start a program on your desktop in the background, e.g. "firefox https://example.com".

    It runs detached, so this returns right away; take a screenshot after a moment
    if the window is slow to appear.
    """
    argv = shlex.split(command)
    if not argv or shutil.which(argv[0]) is None:
        raise DesktopError(f"not found on this desktop: {argv[0] if argv else command!r}")
    subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    if screenshot:
        time.sleep(1.5)  # most windows need a beat to map
    return _result(f"launched {argv[0]}", screenshot)


@mcp.tool(structured_output=False)
def wait(seconds: float = 1.0, screenshot: bool = True) -> str | list:
    """Wait for something to load (max 30 s), then look."""
    time.sleep(max(0.0, min(seconds, 30.0)))
    return _result(f"waited {seconds}s", screenshot)


def start_xvfb(display: str, width: int, height: int) -> None:
    """Start a private Xvfb (plus a window manager if one is installed)."""
    if shutil.which("Xvfb") is None:
        raise SystemExit("Xvfb is not installed (apt install xvfb xdotool)")
    procs = [
        subprocess.Popen(
            ["Xvfb", display, "-screen", "0", f"{width}x{height}x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    ]
    os.environ["DISPLAY"] = display
    for _ in range(50):
        if subprocess.run(["xdotool", "getmouselocation"], capture_output=True).returncode == 0:
            break
        time.sleep(0.1)
    else:
        procs[0].terminate()
        raise SystemExit(f"Xvfb did not come up on {display}")
    for wm in ("fluxbox", "openbox", "xfwm4", "matchbox-window-manager"):
        if shutil.which(wm):
            procs.append(
                subprocess.Popen([wm], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            )
            break

    def _cleanup() -> None:
        for p in reversed(procs):
            p.terminate()

    atexit.register(_cleanup)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--start-xvfb",
        action="store_true",
        help="start a private virtual display for this process (native Linux mode)",
    )
    parser.add_argument("--display", default=os.environ.get("SIDECAR_DISPLAY", ":99"))
    parser.add_argument("--width", type=int, default=int(os.environ.get("WIDTH", "1280")))
    parser.add_argument("--height", type=int, default=int(os.environ.get("HEIGHT", "800")))
    args = parser.parse_args()

    if args.start_xvfb:
        start_xvfb(args.display, args.width, args.height)
    elif not os.environ.get("DISPLAY"):
        raise SystemExit("DISPLAY is not set; pass --start-xvfb or run inside the Docker image")

    if args.transport == "stdio":
        mcp.run("stdio")
    else:
        # Inside Docker we bind 0.0.0.0, which disables the SDK's automatic
        # localhost-only Host check, so set it explicitly.
        security = TransportSecuritySettings(
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"],
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"],
        )
        mcp.run(
            "streamable-http", host=args.host, port=args.port, transport_security=security
        )


if __name__ == "__main__":
    main()
