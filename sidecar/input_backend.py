"""Input/capture backends so the same tools work on Linux, Windows and macOS.

- ``XdotoolBackend`` drives an X11 display (real or Xvfb) via ``xdotool``. This is
  what the Docker image and the isolated Linux mode use.
- ``PyAutoGuiBackend`` drives the *real* desktop on whatever OS Python runs on,
  via ``pyautogui``. This is how Windows and macOS work, where there is no Xvfb:
  Claude shares your actual screen, so it is for the local, "I'm already logged
  in" mode rather than the isolated one.

Each backend owns its own key-name translation, because xdotool keysyms
("Return", "ctrl+l") and pyautogui key names ("enter", "ctrl") differ.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Protocol

import mss
import mss.tools


class BackendError(RuntimeError):
    """Raised for backend-level failures (missing dependency, command failed)."""


# Canonical modifier/key tokens the server speaks; each backend maps these to its
# own vocabulary. Anything not listed is treated as a literal key name.
_ALIASES = {
    "enter": "return", "return": "return", "esc": "escape", "escape": "escape",
    "backspace": "backspace", "delete": "delete", "del": "delete", "tab": "tab",
    "space": "space", "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end", "pageup": "pageup", "page_up": "pageup",
    "pagedown": "pagedown", "page_down": "pagedown", "insert": "insert",
    "ctrl": "ctrl", "control": "ctrl", "ctl": "ctrl",
    "shift": "shift", "alt": "alt", "option": "alt",
    "super": "super", "cmd": "super", "win": "super", "windows": "super",
    "meta": "super",
}


def parse_combo(combo: str) -> list[str]:
    """Split "Ctrl+Shift+T" into canonical tokens ["ctrl", "shift", "t"]."""
    parts = [p.strip() for p in combo.replace(" ", "").split("+") if p.strip()]
    if not parts:
        raise BackendError("empty key combo")
    return [_ALIASES.get(p.lower(), p) for p in parts]


class Backend(Protocol):
    name: str

    def screen_size(self) -> tuple[int, int]: ...
    def capture_png(self) -> bytes: ...
    def move(self, x: int, y: int) -> None: ...
    def click(self, x: int, y: int, button: str, clicks: int) -> None: ...
    def drag(self, x1: int, y1: int, x2: int, y2: int) -> None: ...
    def scroll(self, x: int, y: int, direction: str, amount: int) -> None: ...
    def type_text(self, text: str, delay_ms: int) -> None: ...
    def key(self, combo: str, repeat: int, delay_ms: int) -> None: ...
    def cursor_position(self) -> tuple[int, int]: ...


def _mss_screen_size() -> tuple[int, int]:
    with mss.MSS() as sct:
        mon = sct.monitors[0]
        return mon["width"], mon["height"]


def _mss_capture_png() -> bytes:
    with mss.MSS() as sct:
        shot = sct.grab(sct.monitors[0])
        return mss.tools.to_png(shot.rgb, shot.size)


class XdotoolBackend:
    """X11 backend (Linux). Used for Docker and isolated-Xvfb modes."""

    name = "xdotool"

    _BUTTONS = {"left": 1, "middle": 2, "right": 3}
    _SCROLL = {"up": 4, "down": 5, "left": 6, "right": 7}
    # Canonical token -> xdotool keysym (identity for most; these differ in case/name).
    _KEYSYMS = {
        "return": "Return", "escape": "Escape", "backspace": "BackSpace",
        "delete": "Delete", "tab": "Tab", "space": "space", "up": "Up",
        "down": "Down", "left": "Left", "right": "Right", "home": "Home",
        "end": "End", "pageup": "Prior", "pagedown": "Next", "insert": "Insert",
        "super": "super",
    }

    def __init__(self) -> None:
        if shutil.which("xdotool") is None:
            raise BackendError("xdotool is not installed (apt install xdotool)")

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["xdotool", *args], capture_output=True, text=True, timeout=30, check=False
        )
        if result.returncode != 0:
            raise BackendError(f"xdotool {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout

    def _chord(self, combo: str) -> str:
        return "+".join(self._KEYSYMS.get(t, t) for t in parse_combo(combo))

    def screen_size(self) -> tuple[int, int]:
        return _mss_screen_size()

    def capture_png(self) -> bytes:
        return _mss_capture_png()

    def move(self, x: int, y: int) -> None:
        self._run("mousemove", "--sync", str(x), str(y))

    def click(self, x: int, y: int, button: str, clicks: int) -> None:
        self.move(x, y)
        self._run("click", "--repeat", str(clicks), "--delay", "80", str(self._BUTTONS[button]))

    def drag(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.move(x1, y1)
        self._run("mousedown", "1")
        try:
            self.move((x1 + x2) // 2, (y1 + y2) // 2)
            self.move(x2, y2)
        finally:
            self._run("mouseup", "1")

    def scroll(self, x: int, y: int, direction: str, amount: int) -> None:
        self.move(x, y)
        self._run("click", "--repeat", str(amount), "--delay", "30", str(self._SCROLL[direction]))

    def type_text(self, text: str, delay_ms: int) -> None:
        for i in range(0, len(text), 200):  # xdotool is flaky with very long args
            self._run("type", "--delay", str(delay_ms), "--", text[i : i + 200])

    def key(self, combo: str, repeat: int, delay_ms: int) -> None:
        self._run("key", "--repeat", str(repeat), "--delay", str(delay_ms), "--", self._chord(combo))

    def cursor_position(self) -> tuple[int, int]:
        out = self._run("getmouselocation", "--shell")
        vals = dict(line.split("=", 1) for line in out.split() if "=" in line)
        return int(vals["X"]), int(vals["Y"])


class PyAutoGuiBackend:
    """Real-desktop backend (Windows/macOS/Linux) via pyautogui.

    Drives the actual cursor and keyboard of the session Python runs in, so it
    shares the desktop with the user. Intended for local "already logged in" use.
    """

    name = "pyautogui"

    # Canonical token -> pyautogui key name. pyautogui has no "super"; it uses
    # "win" on Windows and "command" on macOS, resolved at construction.
    _KEYS = {
        "return": "enter", "escape": "esc", "backspace": "backspace",
        "delete": "delete", "tab": "tab", "space": "space", "up": "up",
        "down": "down", "left": "left", "right": "right", "home": "home",
        "end": "end", "pageup": "pageup", "pagedown": "pagedown", "insert": "insert",
        "ctrl": "ctrl", "shift": "shift", "alt": "alt",
    }

    def __init__(self) -> None:
        try:
            import pyautogui
        except Exception as e:  # ImportError, or display/permission errors
            raise BackendError(
                "pyautogui is not available. Install with `pip install pyautogui` "
                "(on Linux it also needs a running X server)."
            ) from e
        import platform

        pyautogui.FAILSAFE = False  # we do our own bounds checking
        self._gui = pyautogui
        self._super = "command" if platform.system() == "Darwin" else "win"

    def _keyname(self, token: str) -> str:
        if token == "super":
            return self._super
        if token in self._KEYS:
            return self._KEYS[token]
        # pyautogui key names for letters are lowercase; a chord like ctrl+shift+T
        # carries the shift separately, so fold a lone letter down.
        if len(token) == 1 and token.isalpha():
            return token.lower()
        return token

    def screen_size(self) -> tuple[int, int]:
        return _mss_screen_size()

    def capture_png(self) -> bytes:
        return _mss_capture_png()

    def move(self, x: int, y: int) -> None:
        self._gui.moveTo(x, y)

    def click(self, x: int, y: int, button: str, clicks: int) -> None:
        self._gui.click(x=x, y=y, clicks=clicks, interval=0.08, button=button)

    def drag(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self._gui.moveTo(x1, y1)
        self._gui.dragTo(x2, y2, duration=0.3, button="left")

    def scroll(self, x: int, y: int, direction: str, amount: int) -> None:
        self._gui.moveTo(x, y)
        if direction in ("up", "down"):
            self._gui.scroll(amount * (1 if direction == "up" else -1))
        else:  # horizontal scroll; not supported on every platform
            self._gui.hscroll(amount * (1 if direction == "right" else -1))

    def type_text(self, text: str, delay_ms: int) -> None:
        self._gui.write(text, interval=delay_ms / 1000.0)

    def key(self, combo: str, repeat: int, delay_ms: int) -> None:
        keys = [self._keyname(t) for t in parse_combo(combo)]
        for _ in range(repeat):
            if len(keys) == 1:
                self._gui.press(keys[0])
            else:
                self._gui.hotkey(*keys)

    def cursor_position(self) -> tuple[int, int]:
        pos = self._gui.position()
        return int(pos[0]), int(pos[1])


def make_backend(kind: str) -> Backend:
    """Build a backend. ``kind`` is "xdotool", "pyautogui" or "auto"."""
    import platform

    if kind == "xdotool":
        return XdotoolBackend()
    if kind == "pyautogui":
        return PyAutoGuiBackend()
    if kind == "auto":
        # Linux with an X display -> xdotool (works for Xvfb and real X11);
        # anything else (Windows/macOS) -> pyautogui on the real desktop.
        if platform.system() == "Linux" and shutil.which("xdotool"):
            return XdotoolBackend()
        return PyAutoGuiBackend()
    raise BackendError(f"unknown backend: {kind!r}")
