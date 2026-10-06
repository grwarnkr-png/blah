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

from sidecar.server import normalize_key  # noqa: E402


def test_normalize_key():
    assert normalize_key("Enter") == "Return"
    assert normalize_key("Ctrl+Shift+T") == "ctrl+shift+T"
    assert normalize_key("cmd + l") == "super+l"
    assert normalize_key("alt+F4") == "alt+F4"


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
            args=["-m", "sidecar.server", "--start-xvfb", "--display", ":97"],
            cwd=str(ROOT),
            env={**os.environ, "DISPLAY": ""},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                assert {"screenshot", "click", "type_text", "key", "launch"} <= names

                shot = await session.call_tool("screenshot", {})
                assert "1280x800" in shot.content[0].text
                assert shot.content[1].type == "image"
                assert shot.content[1].mime_type == "image/png"

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

                bad = await session.call_tool("click", {"x": 5000, "y": 5})
                assert bad.is_error
                assert "off-screen" in bad.content[0].text

    anyio.run(run)
    deadline = time.time() + 5
    while not marker.exists() and time.time() < deadline:
        time.sleep(0.1)
    assert marker.read_text().strip() == "sidecar"
