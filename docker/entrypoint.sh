#!/usr/bin/env bash
set -euo pipefail

Xvfb "$DISPLAY" -screen 0 "${WIDTH}x${HEIGHT}x24" -nolisten tcp &
for _ in $(seq 50); do xdotool getmouselocation >/dev/null 2>&1 && break; sleep 0.1; done

fluxbox >/dev/null 2>&1 &

# Viewer for you: VNC on the container's loopback only, exposed via noVNC.
VNC_ARGS=(-display "$DISPLAY" -localhost -forever -shared -nopw -quiet -rfbport 5900)
[[ "${VIEW_ONLY:-0}" == "1" ]] && VNC_ARGS+=(-viewonly)
x11vnc "${VNC_ARGS[@]}" >/dev/null 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &

cd /opt/sidecar/app
exec /opt/sidecar/bin/python -m sidecar.server --transport http --host 0.0.0.0 --port 8765
