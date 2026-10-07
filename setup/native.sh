#!/usr/bin/env bash
# Native mode for macOS / Linux: Claude drives your REAL desktop and uses your
# actual open windows and installed apps. While it acts, it shares your one
# mouse cursor. For the no-conflict isolated desktop instead, use start.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }
die() { printf "\n\033[1;31mX  %s\033[0m\n" "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "Python 3 is not installed."
command -v claude  >/dev/null 2>&1 || die "Claude Code is not installed."

say "Setting up native mode (about a minute)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt pyautogui

say "Connecting native mode to Claude Code"
PY="$(pwd)/.venv/bin/python"
SRV="$(pwd)/sidecar/server.py"
claude mcp remove sidecar-desktop-native >/dev/null 2>&1 || true
claude mcp add --scope user sidecar-desktop-native -- "$PY" "$SRV" --native

cat <<'DONE'

  Native mode installed as 'sidecar-desktop-native'.

  Claude can now use your REAL desktop - your open windows and installed apps -
  and read/write files under your home folder.

  Heads up:
  - While Claude clicks/types it moves your real mouse; let an action finish
    before you grab the cursor back.
  - macOS: the first run will ask you to grant Accessibility and Screen
    Recording permission to your terminal/Python in System Settings > Privacy.

DONE
