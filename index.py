"""Eternego — single entry point for the CLI and daemon."""

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass

# PyInstaller-bundled Python doesn't pick up the host system's CA store, so
# urllib calls (telegram getMe, discord polling) fail TLS verification with
# "self-signed certificate in certificate chain". Point ssl at certifi
# explicitly — does no harm in dev (env var only takes effect if unset).
import certifi as _certifi
os.environ.setdefault("SSL_CERT_FILE", _certifi.where())

from application.platform import logger, objects
from application.platform.observer import Event, Plan, Signal, subscribe
from config.application import log_file, persona_log_file, signal_log_file
from config.web import HOST as DEFAULT_HOST, PORT as DEFAULT_PORT


@dataclass
class Config:
    debug: bool
    verbosity: int
    host: str
    port: int


def bootstrap(args) -> Config:
    """Shared initialization for all commands — logging, signals, config."""
    config = Config(
        debug=getattr(args, "debug", False),
        verbosity=getattr(args, "verbose", 0),
        host=getattr(args, "host", "127.0.0.1"),
        port=getattr(args, "port", 5001),
    )

    log_file().parent.mkdir(parents=True, exist_ok=True)

    levels = list(logger.Level)
    info_index = levels.index(logger.Level.INFO)

    def persona_id_from(context):
        if not isinstance(context, dict):
            return None
        p = context.get("persona")
        return getattr(p, "id", None) if p is not None else None

    def log_media(message):
        if not config.debug and message.level == logger.Level.DEBUG:
            return
        logger.file_media(log_file)(message)
        if config.debug:
            pid = persona_id_from(message.context)
            if pid:
                logger.file_media(lambda: persona_log_file(pid))(message)
        if config.verbosity >= 3 or (config.verbosity >= 2 and levels.index(message.level) <= info_index):
            print(f"[{message.level.value}] {message.title}", objects.safe(message.context))

    def log_signal(signal: Signal):
        def signal_log_media(message):
            if config.debug:
                logger.file_media(signal_log_file)(message)
                pid = persona_id_from(message.context)
                if pid:
                    logger.file_media(lambda: persona_log_file(pid))(message)
        logger.info(signal.title, {"_type": signal.__class__.__name__, **signal.details}, signal_log_media)
        if config.verbosity >= 2 or (config.verbosity >= 1 and isinstance(signal, (Plan, Event))):
            print(f"[{signal.__class__.__name__}] {signal.title}", objects.safe(signal.details))

    logger.default_media(log_media)
    subscribe(log_signal)

    return config


def main():
    parser = argparse.ArgumentParser(
        prog="eternego",
        description="Eternego AI persona manager",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging and signal file output")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (repeatable)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Web server port (default: {DEFAULT_PORT})")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Web server host (default: {DEFAULT_HOST})")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # launch — entry point for the desktop app wrappers (.app / installer.exe / .AppImage)
    sub.add_parser("launch", help="Start the daemon and open the dashboard in the default browser")

    # daemon — internal, called by systemd or developer
    sub.add_parser("daemon", help="Run the daemon process (used by OS service manager or for development)")

    # service — OS service management
    svc_p = sub.add_parser("service", help="Manage the Eternego background service")
    svc_sub = svc_p.add_subparsers(dest="action", metavar="ACTION")
    svc_start = svc_sub.add_parser("start", help="Register and start the service")
    svc_start.add_argument("--debug", dest="svc_debug", action="store_true",
                           help="Run the background service with debug logging")
    svc_start.add_argument("-v", "--verbose", dest="svc_verbose", action="count", default=0,
                           help="Verbosity for the background service (repeatable)")
    svc_sub.add_parser("stop", help="Stop the service")
    svc_restart = svc_sub.add_parser("restart", help="Restart the service")
    svc_restart.add_argument("--debug", dest="svc_debug", action="store_true",
                             help="Run the background service with debug logging")
    svc_restart.add_argument("-v", "--verbose", dest="svc_verbose", action="count", default=0,
                             help="Verbosity for the background service (repeatable)")
    svc_sub.add_parser("status", help="Show service status")
    svc_sub.add_parser("logs", help="Follow service logs")

    # uninstall
    sub.add_parser("uninstall", help="Remove the Eternego service and source code (preserves persona data)")

    # env
    env_p = sub.add_parser("env", help="Check and prepare the environment")
    env_sub = env_p.add_subparsers(dest="action", metavar="ACTION")
    env_check = env_sub.add_parser("check", help="Check if a model is available and running")
    env_check.add_argument("--model", required=True, help="Model name to check")
    env_prepare = env_sub.add_parser("prepare", help="Install dependencies and pull a model")
    env_prepare.add_argument("--model", default="", help="Model to pull (uses Ollama default if omitted)")

    # When the macOS .app bundle launches from Finder/Dock, no argv is passed
    # but LSEnvironment in Info.plist sets this flag. Treat it as `launch`.
    if len(sys.argv) == 1 and os.environ.get("ETERNEGO_LAUNCH_FROM_BUNDLE") == "1":
        sys.argv.append("launch")

    args = parser.parse_args()

    if args.command == "daemon":
        config = bootstrap(args)
        from daemon import run
        asyncio.run(run(config))

    elif args.command == "launch":
        config = bootstrap(args)
        # Frozen .app (macOS) and .exe (Windows) get the tray-icon launcher so the
        # user has a persistent affordance to reopen the dashboard. Linux .AppImage
        # and the dev/source path keep the simpler browser-only launcher.
        if getattr(sys, "frozen", False) and sys.platform in ("darwin", "win32"):
            from installation.desktop import run as desktop_run
            desktop_run(config)
        else:
            from cli.launch import run as launch_run
            asyncio.run(launch_run(config))

    elif args.command == "service":
        from cli.service import dispatch
        dispatch(args)

    elif args.command == "uninstall":
        from cli.uninstall import run
        run()

    elif args.command == "env":
        config = bootstrap(args)
        from cli.env import dispatch
        asyncio.run(dispatch(args))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
