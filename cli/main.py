"""Eternego CLI — manage the background service and environment."""

import argparse
import asyncio
import os
import platform
import subprocess
import sys


# ── daemon ────────────────────────────────────────────────────────────────────

def cmd_daemon(args):
    """Run the background daemon (called by the OS service manager)."""
    service_args = ["eternego-daemon"]
    service_args += ["-v"] * getattr(args, "verbose", 0)
    if getattr(args, "predict_interval", 60) != 60:
        service_args += ["--predict-interval", str(args.predict_interval)]
    if getattr(args, "port", 5001) != 5001:
        service_args += ["--port", str(args.port)]
    if getattr(args, "host", "127.0.0.1") != "127.0.0.1":
        service_args += ["--host", args.host]
    sys.argv = service_args
    from service import main
    asyncio.run(main())


# ── service management ────────────────────────────────────────────────────────

_OS = platform.system()  # "Linux", "Darwin", or "Windows"

def cmd_service_start(_):
    if _OS == "Linux":
        subprocess.run(["systemctl", "--user", "start", "eternego"])
    elif _OS == "Darwin":
        subprocess.run(["launchctl", "start", "com.eternego"])
    elif _OS == "Windows":
        subprocess.run(["powershell", "-Command", "Start-ScheduledTask -TaskName Eternego"])

def cmd_service_stop(_):
    if _OS == "Linux":
        subprocess.run(["systemctl", "--user", "stop", "eternego"])
    elif _OS == "Darwin":
        subprocess.run(["launchctl", "stop", "com.eternego"])
    elif _OS == "Windows":
        subprocess.run(["powershell", "-Command", "Stop-ScheduledTask -TaskName Eternego"])

def cmd_service_restart(_):
    if _OS == "Linux":
        subprocess.run(["systemctl", "--user", "restart", "eternego"])
    elif _OS == "Darwin":
        uid = os.getuid()
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/com.eternego"])
    elif _OS == "Windows":
        cmd_service_stop(None)
        cmd_service_start(None)

def cmd_service_status(_):
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

def cmd_service_logs(_):
    from config.application import log_file
    path = str(log_file())
    try:
        if _OS == "Windows":
            subprocess.run(["powershell", "-Command", f"Get-Content -Wait -Path '{path}'"])
        else:
            subprocess.run(["tail", "-f", path])
    except KeyboardInterrupt:
        pass


# ── pairing ───────────────────────────────────────────────────────────────────

def cmd_pair(args):
    import json
    import urllib.error
    import urllib.request
    from config import web as web_config

    service_url = f"http://{web_config.HOST}:{web_config.PORT}"
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f"{service_url}/api/pair/{args.code}",
                method="POST",
            )
        )
        print("Channel paired successfully.")
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        print(f"Error: {body.get('detail', 'Unknown error')}")
        sys.exit(1)
    except urllib.error.URLError:
        print(f"Error: Could not connect to the Eternego service at {service_url}. Is it running?")
        sys.exit(1)


# ── environment ───────────────────────────────────────────────────────────────

def cmd_env_check(args):
    from application.business import environment

    async def run():
        outcome = await environment.check_model(args.model)
        if not outcome.success:
            print(f"Not ready: {outcome.message}")
            sys.exit(1)
        print(f"Model '{args.model}' is ready.")

    asyncio.run(run())


def cmd_env_prepare(args):
    from application.business import environment

    async def run():
        outcome = await environment.prepare(args.model or None)
        if not outcome.success:
            print(f"Error: {outcome.message}")
            sys.exit(1)
        model = (outcome.data or {}).get("model", "")
        print(f"Environment is ready. Model: {model}")

    asyncio.run(run())


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="eternego",
        description="Eternego AI persona manager",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # daemon
    daemon_p = sub.add_parser("daemon", help="Run the background daemon (used by the OS service manager)")
    daemon_p.add_argument("-v", "--verbose", action="count", default=0)
    daemon_p.add_argument("--predict-interval", type=int, default=60, metavar="SECONDS",
                          help="Seconds between predict cycles (default: 60, 0 to disable)")
    daemon_p.add_argument("--port", type=int, default=5001, help="Web server port (default: 5001)")
    daemon_p.add_argument("--host", default="127.0.0.1", help="Web server host (default: 127.0.0.1)")

    # service
    svc_p = sub.add_parser("service", help="Manage the Eternego background service")
    svc_sub = svc_p.add_subparsers(dest="action", metavar="ACTION")
    svc_sub.add_parser("start",   help="Start the service")
    svc_sub.add_parser("stop",    help="Stop the service")
    svc_sub.add_parser("restart", help="Restart the service")
    svc_sub.add_parser("status",  help="Show service status")
    svc_sub.add_parser("logs",    help="Follow service logs")

    # pair
    pair_p = sub.add_parser("pair", help="Pair a channel using a code sent by the persona")
    pair_p.add_argument("code", help="6-character pairing code")

    # env
    env_p = sub.add_parser("env", help="Check and prepare the environment")
    env_sub = env_p.add_subparsers(dest="action", metavar="ACTION")

    env_check = env_sub.add_parser("check", help="Check if a model is available and running")
    env_check.add_argument("--model", required=True, help="Model name to check")

    env_prepare = env_sub.add_parser("prepare", help="Install dependencies and pull a model")
    env_prepare.add_argument("--model", default="", help="Model to pull (uses Ollama default if omitted)")

    args = parser.parse_args()

    if args.command == "pair":
        cmd_pair(args)

    elif args.command == "daemon":
        cmd_daemon(args)

    elif args.command == "service":
        dispatch = {
            "start":   cmd_service_start,
            "stop":    cmd_service_stop,
            "restart": cmd_service_restart,
            "status":  cmd_service_status,
            "logs":    cmd_service_logs,
        }
        fn = dispatch.get(getattr(args, "action", None))
        if fn:
            fn(args)
        else:
            svc_p.print_help()

    elif args.command == "env":
        dispatch = {
            "check":   cmd_env_check,
            "prepare": cmd_env_prepare,
        }
        fn = dispatch.get(getattr(args, "action", None))
        if fn:
            fn(args)
        else:
            env_p.print_help()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
