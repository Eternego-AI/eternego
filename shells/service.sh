#!/usr/bin/env bash
# Register Eternego as a system service (systemd on Linux, launchd on macOS).
# This script is for initial installation only (before the CLI exists).
# After install, use `eternego service start [--debug] [-v]` to update flags.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ETERNEGO_BIN="$SCRIPT_DIR/.venv/bin/eternego"

print "Registering service... estimation 1 minute"

if [ "$OS_TYPE" = "Linux" ]; then
    SERVICE_DIR="$HOME/.config/systemd/user"
    run mkdir -p "$SERVICE_DIR"
    cat > "$SERVICE_DIR/eternego.service" <<EOF
[Unit]
Description=Eternego AI Persona Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=$ETERNEGO_BIN daemon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
    run systemctl --user daemon-reload
    run systemctl --user enable eternego
    run loginctl enable-linger "$USER"

elif [ "$OS_TYPE" = "Darwin" ]; then
    PLIST_DIR="$HOME/Library/LaunchAgents"
    SVC_LOG="$HOME/Library/Logs/eternego.log"
    run mkdir -p "$PLIST_DIR"
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
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONDONTWRITEBYTECODE</key>
        <string>1</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$SVC_LOG</string>
    <key>StandardErrorPath</key>
    <string>$SVC_LOG</string>
</dict>
</plist>
EOF
    run launchctl load -w "$PLIST_DIR/com.eternego.plist"
fi
