#!/usr/bin/env bash
# Copy the project to ~/.eternego/source/ so the service runs from a stable location.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INSTALL_DIR="$HOME/.eternego/source"

print "Installing to $INSTALL_DIR"

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# cp -a is more portable than rsync (no extra dependency).
# tar with --exclude pipes through to avoid copying unwanted dirs.
tar -cf - \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    -C "$SCRIPT_DIR" . | tar -xf - -C "$INSTALL_DIR"

# Expose the installed location; install.sh switches SCRIPT_DIR explicitly.
ETERNEGO_INSTALL_DIR="$INSTALL_DIR"
