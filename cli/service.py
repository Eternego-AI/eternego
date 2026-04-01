"""CLI service commands — manage the Eternego OS service."""

import os
import platform
import subprocess
import sys
from pathlib import Path

from config.application import log_file

_OS = platform.system()


def _run(cmd, *, quiet=False, **kwargs):
    """Run a subprocess command and print stderr on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0 and not quiet:
        label = cmd[0] if isinstance(cmd, list) else cmd
        print(f"Error running {label} (exit {result.returncode})")
        if result.stderr and result.stderr.strip():
            print(f"  {result.stderr.strip()}")
    return result
_PROJECT_ROOT = Path(__file__).parent.parent

if _OS == "Windows":
    _ETERNEGO_BIN = str(_PROJECT_ROOT / ".venv" / "Scripts" / "eternego.exe")
else:
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
    _run(["systemctl", "--user", "daemon-reload"])
    _run(["systemctl", "--user", "enable", "eternego"])


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


def _launchd_target() -> str:
    return f"gui/{os.getuid()}"


def _launchd_service() -> str:
    return f"gui/{os.getuid()}/com.eternego"


def _launchd_plist() -> str:
    return str(Path.home() / "Library" / "LaunchAgents" / "com.eternego.plist")


def _write_windows_task(args) -> None:
    """Register the Eternego Windows scheduled task."""
    exec_args = _build_exec_args(args)
    exe = exec_args[0]
    arguments = " ".join(exec_args[1:]) if len(exec_args) > 1 else ""
    ps_cmd = (
        f"$Action = New-ScheduledTaskAction -Execute '{exe}'"
        f" -Argument '{arguments}' -WorkingDirectory '{_PROJECT_ROOT}';"
        f" $Trigger = New-ScheduledTaskTrigger -AtLogOn;"
        f" $Settings = New-ScheduledTaskSettingsSet"
        f" -ExecutionTimeLimit ([TimeSpan]::Zero)"
        f" -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1);"
        f" Register-ScheduledTask -TaskName 'Eternego'"
        f" -Action $Action -Trigger $Trigger"
        f" -Settings $Settings -Force"
    )
    _run(["powershell", "-Command", ps_cmd])


def cmd_start(args):
    if _OS == "Linux":
        _write_systemd_unit(args)
        _run(["systemctl", "--user", "start", "eternego"])
    elif _OS == "Darwin":
        _write_launchd_plist(args)
        _run(["launchctl", "bootout", _launchd_service()], quiet=True)
        _run(["launchctl", "bootstrap", _launchd_target(), _launchd_plist()])
    elif _OS == "Windows":
        _write_windows_task(args)
        _run(["powershell", "-Command", "Start-ScheduledTask -TaskName Eternego"])


def cmd_stop(_):
    if _OS == "Linux":
        _run(["systemctl", "--user", "stop", "eternego"])
    elif _OS == "Darwin":
        _run(["launchctl", "bootout", _launchd_service()])
    elif _OS == "Windows":
        _run(["powershell", "-Command", "Stop-ScheduledTask -TaskName Eternego"])


def cmd_restart(args):
    if _OS == "Linux":
        _write_systemd_unit(args)
        _run(["systemctl", "--user", "restart", "eternego"])
    elif _OS == "Darwin":
        _write_launchd_plist(args)
        _run(["launchctl", "bootout", _launchd_service()], quiet=True)
        _run(["launchctl", "bootstrap", _launchd_target(), _launchd_plist()])
    elif _OS == "Windows":
        _write_windows_task(args)
        _run(["powershell", "-Command",
              "Stop-ScheduledTask -TaskName Eternego; Start-ScheduledTask -TaskName Eternego"])


def cmd_status(_):
    try:
        if _OS == "Linux":
            subprocess.run(["systemctl", "--user", "status", "eternego"])
        elif _OS == "Darwin":
            subprocess.run(["launchctl", "print", _launchd_service()])
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
