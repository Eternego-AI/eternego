#!/bin/sh
# Eternego container entrypoint — starts the X stack, then always runs the daemon.

set -e

if [ "${START_DESKTOP:-true}" = "true" ]; then
    echo "Starting X11 desktop stack..."
    # Clear any stale lock + socket from a previous ungraceful exit, otherwise
    # Xvfb refuses to start with "Server is already active for display N".
    DISPLAY_NUM=$(echo "${DISPLAY:-:99}" | sed 's/^://')
    rm -f "/tmp/.X${DISPLAY_NUM}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM}"
    Xvfb "${DISPLAY:-:99}" -screen 0 "${XVFB_RESOLUTION:-1280x720x24}" -ac +extension GLX +render -noreset &

    until xdpyinfo -display "${DISPLAY:-:99}" >/dev/null 2>&1; do
      sleep 0.2
    done

    fluxbox -display "${DISPLAY:-:99}" >/dev/null 2>&1 &
    x11vnc -display "${DISPLAY:-:99}" -forever -shared -rfbport 5900 -nopw -quiet -bg
    websockify --web=/usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &
    echo "Desktop stack ready."
fi

# Always run the daemon. dbus-run-session starts a session bus, exports
# DBUS_SESSION_BUS_ADDRESS, and exec's the wrapped command in that env —
# the persona's screenshot path goes through xdg-desktop-portal over dbus.
if [ "${DEBUG:-false}" = "true" ]; then
    echo "=== Eternego starting in DEBUG mode ==="
    exec dbus-run-session -- python3 /app/index.py --debug -vvv daemon
else
    echo "=== Eternego starting normal ==="
    exec dbus-run-session -- python3 /app/index.py daemon
fi