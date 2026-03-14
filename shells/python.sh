#!/usr/bin/env bash
# Ensure Python 3.11+ is available.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

python_ok() {
    command -v python3 &>/dev/null || return 1
    python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null
}

if python_ok; then
    print "Python $(python3 --version) already installed"
else
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
        run brew install python@3.11
        run brew link --force python@3.11
    fi
fi
