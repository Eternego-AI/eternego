#!/bin/sh
# Eternego container entrypoint — starts the X stack (Xvfb + fluxbox + x11vnc +
# noVNC) so the persona has her own desktop, then runs the daemon.
#
# Debug mode: Set DEBUG=true (environment variable) or pass --debug as argument.
# This works both in production and development.

set -e

# Support both ways:
# 1. Environment variable (preferred in docker-compose)
# 2. Command-line argument (for manual docker run)
if [ "${DEBUG:-false}" = "true" ] || [ "$1" = "--debug" ]; then
    DEBUG_MODE="--debug"
    # Remove --debug from positional args if it was passed that way
    [ "$1" = "--debug" ] && shift
    echo "=== Eternego starting in DEBUG mode ==="
else
    DEBUG_MODE=""
    echo "=== Eternego starting ==="
fi

if [ "${START_DESKTOP:-true}" = "true" ]; then
    echo "Starting X11 desktop stack..."
    Xvfb "${DISPLAY:-:99}" -screen 0 "${XVFB_RESOLUTION:-1280x720x24}" -ac +extension GLX +render -noreset &

    until xdpyinfo -display "${DISPLAY:-:99}" >/dev/null 2>&1; do
      sleep 0.2
    done

    fluxbox -display "${DISPLAY:-:99}" >/dev/null 2>&1 &
    x11vnc -display "${DISPLAY:-:99}" -forever -shared -rfbport 5900 -nopw -quiet -bg
    websockify --web=/usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &

    echo "Desktop stack ready."
fi

exec python /app/index.py $DEBUG_MODE "$@"