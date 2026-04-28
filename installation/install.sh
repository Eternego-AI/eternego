#!/usr/bin/env bash
# Eternego installer — sets up the CLI and a persistent background service.
# Supports Linux (systemd) and macOS (launchd).
#
# Run from a clone:
#     bash installation/install.sh           # light install (no fine-tuning deps)
#     bash installation/install.sh --full    # full install (includes training extras)
#
# Run remotely (curl pipe):
#     curl -fsSL https://eternego.ai/install.sh | bash
#     curl -fsSL https://eternego.ai/install.sh | bash -s -- --full
#
# Override the version (default: latest GitHub release):
#     ETERNEGO_VERSION=v0.1.0-rc1 bash installation/install.sh
set -e

# HERE = directory of install.sh (always the installation/ dir).
# SCRIPT_DIR = repo source root (parent of installation/). The shells/ helpers
# treat it as "where the project lives" — venv, .env, package, service, etc.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || pwd)"
SCRIPT_DIR="$(cd "$HERE/.." 2>/dev/null && pwd || pwd)"
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
if [ ! -d "$HERE/shells" ]; then
    echo "Downloading Eternego..."
    VERSION="${ETERNEGO_VERSION:-}"
    if [ -z "$VERSION" ]; then
        # Prefer stable; /releases/latest skips prereleases and 404s when only prereleases exist.
        VERSION="$(curl -fsSL https://api.github.com/repos/Eternego-AI/eternego/releases/latest 2>/dev/null \
            | grep '"tag_name"' | head -1 | cut -d '"' -f 4)"
    fi
    if [ -z "$VERSION" ]; then
        # Fall back to the most recent release of any kind (covers prerelease-only state).
        VERSION="$(curl -fsSL https://api.github.com/repos/Eternego-AI/eternego/releases \
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
    HERE="$TMP_DIR/installation"
    echo "Eternego $VERSION downloaded to $SCRIPT_DIR"
fi

. "$HERE/shells/lib.sh"

on_exit() {
    local code=$?
    if [ $code -ne 0 ]; then
        print ""
        print "Installation failed or was interrupted. Log: $LOG_FILE"
    fi
}
trap on_exit EXIT

. "$HERE/shells/banner.sh"
. "$HERE/shells/copy.sh"
# From here on, operate on the installed copy
SCRIPT_DIR="$ETERNEGO_INSTALL_DIR"
HERE="$SCRIPT_DIR/installation"
. "$HERE/shells/python.sh"
. "$HERE/shells/packages.sh"
. "$HERE/shells/gguf.sh"
. "$HERE/shells/env.sh"
. "$HERE/shells/service.sh"
. "$HERE/shells/start.sh"

print "Dashboard is accessible at http://$WEB_HOST:$WEB_PORT"
