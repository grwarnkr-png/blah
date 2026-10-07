"""End-to-end: talk MCP to the server over stdio, drive xterm on a private Xvfb."""

import os
import shutil
import sys
import time
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.input_backend import XdotoolBackend, parse_combo  # noqa: E402
from sidecar.files import FileAccessError, FileScope  # noqa: E402


def test_parse_combo():
    assert parse_combo("Enter") == ["return"]
    assert parse_combo("Ctrl+Shift+T") == ["ctrl", "shift", "T"]
    assert parse_combo("cmd + l") == ["super", "l"]
    assert parse_combo("alt+F4") == ["alt", "F4"]


def test_xdotool_chord_mapping():
    b = XdotoolBackend.__new__(XdotoolBackend)  # skip the which() check
    assert b._chord("Enter") == "Return"
    assert b._chord("Ctrl+Shift+T") == "ctrl+shift+T"
    assert b._chord("cmd+l") == "super+l"
    assert b._chord("alt+F4") == "alt+F4"


def test_file_scope_confinement(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "notes.txt").write_text("hello")
    scope = FileScope(root)
    assert scope.read_file("notes.txt") == "hello"
    assert "notes.txt" in scope.list_dir(".")
    scope.write_file("sub/new.txt", "x")
    assert (root / "sub" / "new.txt").read_text() == "x"
    for bad in ("../outside.txt", "/etc/passwd", "sub/../../escape"):
        with pytest.raises(FileAccessError):
            scope.read_file(bad)


needs_x = pytest.mark.skipif(
    not all(shutil.which(b) for b in ("Xvfb", "xdotool", "xterm")),
    reason="needs Xvfb, xdotool and xterm",
)


@needs_x
def test_drives_a_private_display(tmp_path):
    marker = tmp_path / "typed.txt"

    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "sidecar.server", "--start-xvfb", "--display", ":97",
                  "--file-root", str(tmp_path)],
            cwd=str(ROOT),
            env={**os.environ, "DISPLAY": ""},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                assert {"screenshot", "click", "type_text", "key", "launch",
                        "about", "list_dir", "read_file", "write_file"} <= names

                about = await session.call_tool("about", {})
                assert "isolated" in about.content[0].text

                shot = await session.call_tool("screenshot", {})
                assert "1280x800" in shot.content[0].text
                assert shot.content[1].type == "image"
                assert shot.content[1].mime_type in ("image/png", "image/jpeg")

                await session.call_tool(
                    "launch", {"command": "xterm -geometry 80x24+0+0", "screenshot": False}
                )
                await anyio.sleep(1.5)
                await session.call_tool("click", {"x": 100, "y": 100, "screenshot": False})
                await session.call_tool(
                    "type_text", {"text": f"echo sidecar > {marker}", "screenshot": False}
                )
                res = await session.call_tool("key", {"combo": "enter"})
                assert res.content[1].type == "image"

                pos = await session.call_tool("cursor_position", {})
                assert pos.content[0].text == "(100, 100)"

                await session.call_tool(
                    "write_file", {"path": "roundtrip.txt", "content": "via mcp"}
                )
                rf = await session.call_tool("read_file", {"path": "roundtrip.txt"})
                assert rf.content[0].text == "via mcp"
                esc = await session.call_tool("read_file", {"path": "../../../etc/passwd"})
                assert esc.is_error

                bad = await session.call_tool("click", {"x": 5000, "y": 5})
                assert bad.is_error
                assert "off-screen" in bad.content[0].text

    anyio.run(run)
    deadline = time.time() + 5
    while not marker.exists() and time.time() < deadline:
        time.sleep(0.1)
    assert marker.read_text().strip() == "sidecar"
