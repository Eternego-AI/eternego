#!/usr/bin/env bash
# Copy .env.example to .env if not already present.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ETERNEGO_LOGS_DIR="$HOME/.eternego/logs"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    print "Creating .env from .env.example"
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
fi

# Point logs to ~/.eternego/logs so they survive source updates.
if grep -q "^LOGS_DIR=$" "$SCRIPT_DIR/.env" 2>/dev/null; then
    run sed -i.bak "s|^LOGS_DIR=$|LOGS_DIR=$ETERNEGO_LOGS_DIR|" "$SCRIPT_DIR/.env"
    rm -f "$SCRIPT_DIR/.env.bak"
fi

WEB_HOST="$(grep "^WEB_HOST=" "$SCRIPT_DIR/.env" | cut -d= -f2)"
WEB_PORT="$(grep "^WEB_PORT=" "$SCRIPT_DIR/.env" | cut -d= -f2)"
