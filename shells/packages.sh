#!/usr/bin/env bash
# Install Eternego and all Python dependencies inside a virtual environment.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

VENV_DIR="$SCRIPT_DIR/.venv"
PIP_INDEX="--index-url https://pypi.org/simple/"

if [ ! -d "$VENV_DIR" ]; then
    print "Creating virtual environment..."
    run "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# Use venv's Python and pip from here on
PYTHON_BIN="$VENV_DIR/bin/python"

print "Upgrading pip..."
run "$PYTHON_BIN" -m pip install --upgrade pip $PIP_INDEX

print "Installing eternego... estimation 3-5 minutes"
run "$PYTHON_BIN" -m pip install -e "$SCRIPT_DIR" $PIP_INDEX

ETERNEGO_BIN="$VENV_DIR/bin/eternego"
