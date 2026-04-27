"""Eternego daemon — opens the event loop, hands off to manager, waits.

Manager owns everything persona-shaped: connections, heartbeat, schedule,
agent registry, persona loading. Daemon's job is just orchestration of boot
and shutdown plus the HTTP server.
"""

import asyncio
import signal
import sys

import uvicorn

from application.business import environment
from application.platform.observer import set_loop, subscribe
import manager
from web.app import app as web_app
from web.socket import on_signal

_web_server: uvicorn.Server | None = None


async def start_web(host: str, port: int) -> None:
    global _web_server
    config = uvicorn.Config(web_app, host=host, port=port, log_level="error")
    _web_server = uvicorn.Server(config)
    if _web_server is not None:
        await _web_server.serve()


async def run(config):
    """Run the daemon — register observer loop, start manager, start web, wait."""
    set_loop(asyncio.get_running_loop())

    loop = asyncio.get_running_loop()
    shutdown = asyncio.Event()

    subscribe(on_signal)
    manager.on_fatal = shutdown.set   # vital loop dies → shutdown fires
    await manager.start()

    if sys.platform == "win32":
        signal.signal(signal.SIGTERM, lambda *_: shutdown.set())
        signal.signal(signal.SIGINT, lambda *_: shutdown.set())
    else:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, shutdown.set)

    outcome = await environment.ready()
    if not outcome.success:
        print(f"Warning: {outcome.message}")

    web_task = asyncio.create_task(start_web(config.host, config.port))
    web_task.add_done_callback(
        lambda t: print(f"Web server stopped: {t.exception()}") if not t.cancelled() and t.exception() else None
    )

    await shutdown.wait()

    print("Shutting down...")
    await manager.stop()

    if _web_server:
        _web_server.should_exit = True
    try:
        await asyncio.wait_for(web_task, timeout=5)
    except asyncio.TimeoutError:
        web_task.cancel()
