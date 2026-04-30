#!/bin/sh
# Eternego container entrypoint — starts the X stack (Xvfb + fluxbox + x11vnc +
# noVNC) so the persona has her own desktop, then runs the daemon.
#
# Set START_DESKTOP=false at run time to skip the X stack — channels-only deploys
# don't need a screen and Xvfb's idle ~10MB isn't worth paying for.
set -e

if [ "${START_DESKTOP:-true}" = "true" ]; then
    Xvfb "${DISPLAY:-:99}" -screen 0 "${XVFB_RESOLUTION:-1280x720x24}" -ac +extension GLX +render -noreset &
    # Give Xvfb a moment to bind before fluxbox tries to connect.
    sleep 0.3
    fluxbox -display "${DISPLAY:-:99}" >/dev/null 2>&1 &
    # x11vnc listens on the loopback port noVNC bridges to. -nopw is fine because
    # noVNC itself is bound to localhost in the default port mapping; users who
    # publish 6080 to the world should add their own VNC password.
    x11vnc -display "${DISPLAY:-:99}" -forever -shared -rfbport 5900 -nopw -quiet -bg
    # noVNC web client at /usr/share/novnc → http://localhost:6080/vnc.html
    websockify --web=/usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &
fi

exec python /app/index.py daemon
