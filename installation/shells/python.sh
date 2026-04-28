#!/usr/bin/env bash
# Ensure Python 3.11+ is available.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# Find a suitable python3 binary (3.11+)
find_python() {
    for candidate in python3.13 python3.12 python3.11 python3; do
        local bin
        bin="$(command -v "$candidate" 2>/dev/null)" || continue
        if "$bin" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            echo "$bin"
            return 0
        fi
    done
    return 1
}

PYTHON_BIN="$(find_python)" && {
    print "Python $($PYTHON_BIN --version) already installed"
}

if [ -z "$PYTHON_BIN" ]; then
    print "Installing python... estimation 1-2 minutes"

    if [ "$OS_TYPE" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            run sudo apt-get update -q
            run sudo apt-get install -y python3 python3-pip
        elif command -v dnf &>/dev/null; then
            run sudo dnf install -y python3 python3-pip
        elif command -v pacman &>/dev/null; then
            run sudo pacman -S --noconfirm python python-pip
        elif command -v zypper &>/dev/null; then
            run sudo zypper install -y python3 python3-pip
        else
            print "Could not detect a package manager. Please install Python 3.11+ manually."
            exit 1
        fi

    elif [ "$OS_TYPE" = "Darwin" ]; then
        if ! command -v brew &>/dev/null; then
            print "Installing homebrew... estimation 1 minute"
            run /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            if [ -x "/opt/homebrew/bin/brew" ]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            else
                eval "$(/usr/local/bin/brew shellenv)"
            fi
        fi
        run brew install python@3.13
        run brew link --force python@3.13
    fi

    PYTHON_BIN="$(find_python)"
    if [ -z "$PYTHON_BIN" ]; then
        print "Python 3.11+ could not be found after installation. Please install it manually."
        exit 1
    fi
fi

# Export so other scripts use the right binary
export PYTHON_BIN
