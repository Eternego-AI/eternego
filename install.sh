#!/usr/bin/env bash
# Eternego installer — sets up the CLI and a persistent background service.
# Supports Linux (systemd) and macOS (launchd).
# Usage: bash install.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_TYPE="$(uname -s)"

# ── Ensure Python 3.11+ ───────────────────────────────────────────────────────

python_ok() {
    command -v python3 &>/dev/null || return 1
    python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null
}

if ! python_ok; then
    echo "Python 3.11+ not found. Installing ..."

    if [ "$OS_TYPE" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -q && sudo apt-get install -y python3 python3-pip
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3 python3-pip
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm python python-pip
        elif command -v zypper &>/dev/null; then
            sudo zypper install -y python3 python3-pip
        else
            echo "Could not detect a package manager. Please install Python 3.11+ manually."
            exit 1
        fi

    elif [ "$OS_TYPE" = "Darwin" ]; then
        if ! command -v brew &>/dev/null; then
            echo "Installing Homebrew ..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            # Add Homebrew to PATH for the rest of this script
            if [ -x "/opt/homebrew/bin/brew" ]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            else
                eval "$(/usr/local/bin/brew shellenv)"
            fi
        fi
        echo "Installing Python via Homebrew ..."
        brew install python@3.11
        brew link --force python@3.11
    fi
fi

# ── Install Eternego ──────────────────────────────────────────────────────────

echo "Installing Eternego from $SCRIPT_DIR ..."
python3 -m pip install -q -e "$SCRIPT_DIR"

ETERNEGO_BIN="$(python3 -c 'import sysconfig, os; print(os.path.join(sysconfig.get_path("scripts"), "eternego"))')"

# ── Linux (systemd user service) ──────────────────────────────────────────────

if [ "$OS_TYPE" = "Linux" ]; then
    echo "Setting up systemd user service ..."
    SERVICE_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SERVICE_DIR"
    cat > "$SERVICE_DIR/eternego.service" <<EOF
[Unit]
Description=Eternego AI Persona Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$ETERNEGO_BIN daemon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable eternego
    # Start at boot even without an active login session.
    loginctl enable-linger "$USER"

# ── macOS (launchd user agent) ────────────────────────────────────────────────

elif [ "$OS_TYPE" = "Darwin" ]; then
    echo "Setting up launchd user agent ..."
    PLIST_DIR="$HOME/Library/LaunchAgents"
    LOG_FILE="$HOME/Library/Logs/eternego.log"
    mkdir -p "$PLIST_DIR"
    cat > "$PLIST_DIR/com.eternego.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.eternego</string>
    <key>ProgramArguments</key>
    <array>
        <string>$ETERNEGO_BIN</string>
        <string>daemon</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_FILE</string>
    <key>StandardErrorPath</key>
    <string>$LOG_FILE</string>
</dict>
</plist>
EOF
    launchctl load -w "$PLIST_DIR/com.eternego.plist"

else
    echo "Unsupported OS: $OS_TYPE"
    echo "For Windows, run: pwsh install.ps1"
    exit 1
fi

echo ""
echo "Eternego installed successfully."
echo ""
echo "  eternego service start    — start the service"
echo "  eternego service stop     — stop the service"
echo "  eternego service restart  — restart the service"
echo "  eternego service status   — check service status"
echo "  eternego service logs     — follow live logs"
echo "  eternego persona list     — list personas"
echo ""
echo "The service will start automatically on next login/boot."
echo "To start it right now: eternego service start"
