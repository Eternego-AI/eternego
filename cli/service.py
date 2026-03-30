"""CLI service commands — manage the Eternego OS service."""

import os
import platform
import subprocess
import sys
from pathlib import Path

from config.application import log_file

_OS = platform.system()
_PROJECT_ROOT = Path(__file__).parent.parent
_ETERNEGO_BIN = str(_PROJECT_ROOT / ".venv" / "bin" / "eternego")


def _build_exec_args(args) -> list[str]:
    """Build the daemon command line from service start/restart flags."""
    parts = [_ETERNEGO_BIN]
    if getattr(args, "svc_debug", False):
        parts.append("--debug")
    verbose_count = getattr(args, "svc_verbose", 0)
    if verbose_count:
        parts.append("-" + "v" * verbose_count)
    parts.append("daemon")
    return parts


def _write_systemd_unit(args) -> None:
    """Generate and write the systemd user unit file."""
    exec_args = _build_exec_args(args)
    exec_start = " ".join(exec_args)

    unit = f"""[Unit]
Description=Eternego AI Persona Service
After=network.target

[Service]
Type=simple
WorkingDirectory={_PROJECT_ROOT}
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart={exec_start}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    (service_dir / "eternego.service").write_text(unit)
    subprocess.run(["systemctl", "--user", "daemon-reload"])
    subprocess.run(["systemctl", "--user", "enable", "eternego"])


def _write_launchd_plist(args) -> None:
    """Generate and write the launchd plist file."""
    exec_args = _build_exec_args(args)
    args_xml = "\n        ".join(f"<string>{a}</string>" for a in exec_args)

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.eternego</string>
    <key>ProgramArguments</key>
    <array>
        {args_xml}
    </array>
    <key>WorkingDirectory</key>
    <string>{_PROJECT_ROOT}</string>
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
    <string>{Path.home() / "Library" / "Logs" / "eternego.log"}</string>
    <key>StandardErrorPath</key>
    <string>{Path.home() / "Library" / "Logs" / "eternego.log"}</string>
</dict>
</plist>
"""
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True, exist_ok=True)
    (plist_dir / "com.eternego.plist").write_text(plist)


def cmd_start(args):
    if _OS == "Linux":
        _write_systemd_unit(args)
        subprocess.run(["systemctl", "--user", "start", "eternego"])
    elif _OS == "Darwin":
        _write_launchd_plist(args)
        subprocess.run(["launchctl", "load", "-w",
                        str(Path.home() / "Library" / "LaunchAgents" / "com.eternego.plist")])


def cmd_stop(_):
    if _OS == "Linux":
        subprocess.run(["systemctl", "--user", "stop", "eternego"])
    elif _OS == "Darwin":
        subprocess.run(["launchctl", "stop", "com.eternego"])
    elif _OS == "Windows":
        subprocess.run(["powershell", "-Command", "Stop-ScheduledTask -TaskName Eternego"])


def cmd_restart(args):
    if _OS == "Linux":
        _write_systemd_unit(args)
        subprocess.run(["systemctl", "--user", "restart", "eternego"])
    elif _OS == "Darwin":
        _write_launchd_plist(args)
        uid = os.getuid()
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/com.eternego"])


def cmd_status(_):
    try:
        if _OS == "Linux":
            subprocess.run(["systemctl", "--user", "status", "eternego"])
        elif _OS == "Darwin":
            subprocess.run(["launchctl", "list", "com.eternego"])
        elif _OS == "Windows":
            subprocess.run([
                "powershell", "-Command",
                "Get-ScheduledTask -TaskName Eternego | Get-ScheduledTaskInfo",
            ])
    except KeyboardInterrupt:
        pass


def cmd_logs(_):
    path = str(log_file())
    try:
        if _OS == "Windows":
            subprocess.run(["powershell", "-Command", f"Get-Content -Wait -Path '{path}'"])
        else:
            subprocess.run(["tail", "-f", path])
    except KeyboardInterrupt:
        pass


def dispatch(args):
    actions = {
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "status": cmd_status,
        "logs": cmd_logs,
    }
    fn = actions.get(getattr(args, "action", None))
    if fn:
        fn(args)
    else:
        print("Usage: eternego service {start,stop,restart,status,logs}")
        sys.exit(1)
