#!/usr/bin/env bash
# Install Eternego and all Python dependencies.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

PIP_INDEX="--index-url https://pypi.org/simple/"

print "Upgrading pip..."
run "$PYTHON_BIN" -m pip install --upgrade pip $PIP_INDEX

print "Installing eternego... estimation 3-5 minutes"
run "$PYTHON_BIN" -m pip install -e "$SCRIPT_DIR" $PIP_INDEX

ETERNEGO_BIN="$("$PYTHON_BIN" -c 'import sysconfig, os; print(os.path.join(sysconfig.get_path("scripts"), "eternego"))')"
