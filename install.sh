#!/usr/bin/env bash
# Eternego installer — sets up the CLI and a persistent background service.
# Supports Linux (systemd) and macOS (launchd).
#
# Run from a clone:
#     bash install.sh           # light install (no fine-tuning deps)
#     bash install.sh --full    # full install (includes training extras)
#
# Run remotely (curl pipe):
#     curl -fsSL https://eternego.ai/install.sh | bash
#     curl -fsSL https://eternego.ai/install.sh | bash -s -- --full
#
# Override the version (default: latest GitHub release):
#     ETERNEGO_VERSION=v0.1.0-rc1 bash install.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || pwd)"
OS_TYPE="$(uname -s)"
LOG_FILE="/tmp/eternego-install.log"

# Parse flags
INSTALL_FULL=0
for arg in "$@"; do
    case "$arg" in
        --full) INSTALL_FULL=1 ;;
    esac
done
export INSTALL_FULL

# If the install script was downloaded standalone (no shells/ next to it),
# fetch the source tarball from GitHub and continue from the extracted copy.
if [ ! -d "$SCRIPT_DIR/shells" ]; then
    echo "Downloading Eternego..."
    VERSION="${ETERNEGO_VERSION:-}"
    if [ -z "$VERSION" ]; then
        VERSION="$(curl -fsSL https://api.github.com/repos/Eternego-AI/eternego/releases/latest \
            | grep '"tag_name"' | head -1 | cut -d '"' -f 4)"
    fi
    if [ -z "$VERSION" ]; then
        echo "Could not determine Eternego version. Set ETERNEGO_VERSION explicitly."
        exit 1
    fi
    TMP_DIR="$(mktemp -d)"
    curl -fsSL "https://github.com/Eternego-AI/eternego/archive/refs/tags/${VERSION}.tar.gz" \
        | tar -xz -C "$TMP_DIR" --strip-components=1
    SCRIPT_DIR="$TMP_DIR"
    echo "Eternego $VERSION downloaded to $SCRIPT_DIR"
fi

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
