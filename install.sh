#!/usr/bin/env bash
# Eternego installer — sets up the CLI and a persistent background service.
# Supports Linux (systemd) and macOS (launchd).
# Usage: bash install.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_TYPE="$(uname -s)"

step() { echo ""; echo "━━━ $1 ━━━"; }
info() { echo "  → $1"; }

# ── Ensure Python 3.11+ ───────────────────────────────────────────────────────

step "[1/4] Python"

python_ok() {
    command -v python3 &>/dev/null || return 1
    python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null
}

if python_ok; then
    info "Python $(python3 --version) — OK"
else
    info "Python 3.11+ not found. Installing ..."

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
            info "Installing Homebrew ..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            # Add Homebrew to PATH for the rest of this script
            if [ -x "/opt/homebrew/bin/brew" ]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            else
                eval "$(/usr/local/bin/brew shellenv)"
            fi
        fi
        info "Installing Python via Homebrew ..."
        brew install python@3.11
        brew link --force python@3.11
    fi
fi

# ── Install Python packages ───────────────────────────────────────────────────

step "[2/4] Python packages"
info "Installing Eternego and fine-tuning dependencies (torch, transformers, peft, trl, ...)."
info "This step can take several minutes on first install."
echo ""
python3 -m pip install -e "$SCRIPT_DIR[finetune]"

# ── Download GGUF conversion script ──────────────────────────────────────────

step "[3/4] GGUF conversion script"
info "Downloading convert_hf_to_gguf.py from llama.cpp ..."
curl -fsSL \
  "https://raw.githubusercontent.com/ggerganov/llama.cpp/master/convert_hf_to_gguf.py" \
  -o "$SCRIPT_DIR/tools/convert_hf_to_gguf.py" \
  && info "Downloaded to tools/convert_hf_to_gguf.py — OK" \
  || echo "  ⚠ Warning: could not download convert_hf_to_gguf.py — fine-tuning will be unavailable until it is present in tools/"

ETERNEGO_BIN="$(python3 -c 'import sysconfig, os; print(os.path.join(sysconfig.get_path("scripts"), "eternego"))')"

# ── Register system service ───────────────────────────────────────────────────

step "[4/4] System service"

if [ "$OS_TYPE" = "Linux" ]; then
    info "Registering systemd user service ..."
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
    info "Service registered and enabled — OK"

elif [ "$OS_TYPE" = "Darwin" ]; then
    info "Registering launchd user agent ..."
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
    info "Service registered and enabled — OK"

else
    echo "Unsupported OS: $OS_TYPE"
    echo "For Windows, run: pwsh install.ps1"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Eternego installed successfully."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  eternego service start    — start the service"
echo "  eternego service stop     — stop the service"
echo "  eternego service restart  — restart the service"
echo "  eternego service status   — check service status"
echo "  eternego service logs     — follow live logs"
echo "  eternego persona list     — list personas"
echo ""
echo "  The service will start automatically on next login/boot."
echo "  To start it right now: eternego service start"
echo ""
