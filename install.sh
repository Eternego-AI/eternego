#!/usr/bin/env bash
# Eternego installer — sets up the CLI and a persistent background service.
# Supports Linux (systemd) and macOS (launchd).
# Usage: bash install.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_TYPE="$(uname -s)"
LOG_FILE="/tmp/eternego-install.log"

. "$SCRIPT_DIR/shells/lib.sh"

on_exit() {
    local code=$?
    if [ $code -ne 0 ]; then
        print ""
        print "Installation failed or was interrupted. Log: $LOG_FILE"
    fi
}
trap on_exit EXIT

. "$SCRIPT_DIR/shells/banner.sh"
. "$SCRIPT_DIR/shells/copy.sh"
# From here on, operate on the installed copy
SCRIPT_DIR="$ETERNEGO_INSTALL_DIR"
. "$SCRIPT_DIR/shells/python.sh"
. "$SCRIPT_DIR/shells/packages.sh"
. "$SCRIPT_DIR/shells/gguf.sh"
. "$SCRIPT_DIR/shells/env.sh"
. "$SCRIPT_DIR/shells/service.sh"
. "$SCRIPT_DIR/shells/start.sh"

print "Dashboard is accessible at http://$WEB_HOST:$WEB_PORT"
