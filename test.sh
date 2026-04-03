#!/usr/bin/env bash
# Download and run the test runner.
# Copy this file to your project root.
# Usage: bash test.sh [test_directory]
set -e

REPO="Eternego-AI/test-runner"
TMP_DIR="${TMPDIR:-/tmp}/test-runner"

if [ ! -f "$TMP_DIR/run" ]; then
    echo "Downloading test-runner..."
    mkdir -p "$TMP_DIR"

    AUTH=""
    if [ -n "$GITHUB_TOKEN" ]; then
        AUTH="-H \"Authorization: token $GITHUB_TOKEN\""
    fi

    URL=$(eval curl -s $AUTH "https://api.github.com/repos/$REPO/releases/latest" \
        | grep '"browser_download_url".*test-runner.zip' | cut -d'"' -f4)

    if [ -z "$URL" ]; then
        echo "Error: Could not find test-runner release."
        exit 1
    fi

    eval curl -sL $AUTH "$URL" -o "$TMP_DIR/test-runner.zip"
    unzip -qo "$TMP_DIR/test-runner.zip" -d "$TMP_DIR"
    rm "$TMP_DIR/test-runner.zip"
fi

python -u "$TMP_DIR/run" "${1:-tests}"
