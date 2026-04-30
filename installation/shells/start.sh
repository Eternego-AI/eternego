#!/usr/bin/env bash
# Start the Eternego service.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

print "Starting service"

if [ "$OS_TYPE" = "Linux" ]; then
    run systemctl --user start eternego
elif [ "$OS_TYPE" = "Darwin" ]; then
    # bootstrap in service.sh already starts the service via RunAtLoad
    print "Service started"
fi
