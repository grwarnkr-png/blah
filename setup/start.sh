#!/usr/bin/env bash
# One-command setup for Linux (and macOS note below).
# Double-click, or run: ./setup/start.sh
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }
die() { printf "\n\033[1;31mX  %s\033[0m\n" "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "Python 3 is not installed. Install it and run this again."
command -v claude  >/dev/null 2>&1 || die "Claude Code is not installed. Install it and run this again."

OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
  cat <<'MAC'

  macOS can't give Claude an independent on-screen cursor without a second
  login session, so the no-conflict version here runs in Docker instead
  (a private Linux desktop you watch in the browser):

      docker compose up -d --build        # then open http://localhost:6080/vnc.html

  See the README "macOS / Windows" section. Exiting.
MAC
  exit 0
fi

say "Setting up (first run installs a few things, ~1-2 min)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

NEED="xdotool xvfb x11vnc novnc python3-websockify fluxbox"
MISSING=""
for pkg in xdotool Xvfb x11vnc websockify fluxbox; do
  command -v "$pkg" >/dev/null 2>&1 || MISSING="yes"
done
if [ -n "$MISSING" ]; then
  say "Installing the virtual-display tools (needs your password)"
  sudo apt-get update -qq && sudo apt-get install -y -qq $NEED \
    || die "Couldn't install automatically. Run: sudo apt install $NEED"
fi

say "Connecting it to Claude Code"
PY="$(pwd)/.venv/bin/python"
SRV="$(pwd)/sidecar/server.py"
claude mcp remove sidecar-desktop >/dev/null 2>&1 || true
# Independent display (does NOT touch your real cursor) + a browser viewer +
# read/write access rooted at your home folder.
claude mcp add --scope user sidecar-desktop -- \
  "$PY" "$SRV" --start-xvfb --viewer --file-root "$HOME"

cat <<DONE

  All set.

  Claude now has 'sidecar-desktop' tools in every Claude Code session. It gets
  its OWN screen (your real mouse/keyboard stay yours), can run your installed
  apps, and can read/write files under your home folder.

  Start a Claude session and just ask, e.g.
      "use your sidecar desktop to open Firefox and ..."

  Watch it work (while a session is running):  http://localhost:6080/vnc.html

DONE
