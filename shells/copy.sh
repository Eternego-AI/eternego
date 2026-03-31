#!/usr/bin/env bash
# Copy the project to ~/.eternego/source/ so the service runs from a stable location.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INSTALL_DIR="$HOME/.eternego/source"

print "Installing to $INSTALL_DIR"

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

rsync -a \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    "$SCRIPT_DIR/" "$INSTALL_DIR/"

# All subsequent scripts operate on the installed copy
SCRIPT_DIR="$INSTALL_DIR"
