#!/bin/sh
set -eu
cd "$(dirname "$0")"
base="$HOME/.local/share/posting"
export PATH="$PWD/scripts/wsl-bin:$PATH"
# -displayfd with abstract-only Xvfb can pick WSLg's :0. Use the library's
# supported high-number allocator so Chrome/Xlib/Openbox share our Xvfb.
export PYVIRTUALDISPLAY_DISPLAYFD=0
test -x "$base/.venv/bin/uvicorn"
mkdir -p "$HOME/.posting-runtime" "$base/manual"
# Chrome needs Linux sockets and a short socket path (not the Windows mount).
export TMPDIR="$HOME/.posting-runtime"
export DATABASE_PATH="$base/manual/tasks.db"
export BROWSER_PROFILES_ROOT="$base/manual/profiles"
export ARTIFACT_ROOT="$base/manual/artifacts"
mkdir -p "$BROWSER_PROFILES_ROOT"
chmod 700 "$BROWSER_PROFILES_ROOT"
export CHROMIUM_BINARY="$base/browser/chrome-linux64/chrome"
export CHROMEDRIVER_BINARY="$base/browser/chromedriver-linux64/chromedriver"
export SE_CHROMEDRIVER="$CHROMEDRIVER_BINARY"
export SE_OFFLINE=true
export DISPLAY_VIEWER_ASSETS=/opt/posting-novnc
export XDG_RUNTIME_DIR="$base/manual/runtime"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
touch "$HOME/.Xauthority"
exec "$base/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port "${1:-8001}" --workers 1 --reload --reload-dir app --reload-include "*.py" --reload-include ".env" --reload-dir .
