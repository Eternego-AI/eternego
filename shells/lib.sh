#!/usr/bin/env bash
# Shared functions — dot-sourced by sub-shells.
# Requires: LOG_FILE to be set by the caller.

print() {
    echo "$1"
}

run() {
    echo "  Running $*"
    echo "  $ $*" >> "$LOG_FILE"
    "$@" >> "$LOG_FILE" 2>&1
}
