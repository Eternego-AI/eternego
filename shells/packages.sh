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

# Make 'eternego' available system-wide
LINK_DIR="$HOME/.local/bin"
mkdir -p "$LINK_DIR"
ln -sf "$ETERNEGO_BIN" "$LINK_DIR/eternego"

if [[ ":$PATH:" != *":$LINK_DIR:"* ]]; then
    SHELL_RC=""
    if [ -f "$HOME/.zshrc" ]; then SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then SHELL_RC="$HOME/.bashrc"
    fi
    if [ -n "$SHELL_RC" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        print "Added ~/.local/bin to PATH in $SHELL_RC (restart your shell or run: source $SHELL_RC)"
    fi
    export PATH="$LINK_DIR:$PATH"
fi
