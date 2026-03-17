#!/usr/bin/env bash
# Install Eternego and all Python dependencies.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

print "Upgrading pip..."
run python3 -m pip install --upgrade pip

print "Installing eternego... estimation 3-5 minutes"
run python3 -m pip install -e "$SCRIPT_DIR"

ETERNEGO_BIN="$(python3 -c 'import sysconfig, os; print(os.path.join(sysconfig.get_path("scripts"), "eternego"))')"
