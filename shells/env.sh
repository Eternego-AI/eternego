#!/usr/bin/env bash
# Copy .env.example to .env if not already present.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    print "Creating .env from .env.example"
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
fi

WEB_HOST="$(grep "^WEB_HOST=" "$SCRIPT_DIR/.env" | cut -d= -f2)"
WEB_PORT="$(grep "^WEB_PORT=" "$SCRIPT_DIR/.env" | cut -d= -f2)"
