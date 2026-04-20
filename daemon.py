"""Eternego daemon — the business owner that starts the building.

Gives the manager its job description: for each customer, assign an agent.
Runs heartbeat rounds. Shuts down gracefully.
"""

import asyncio
import signal
import sys

import uvicorn

from application.business import environment, persona
from application.platform.observer import subscribe
import manager
from web.app import app as web_app
from web.socket import on_signal

_web_server: uvicorn.Server | None = None


async def start_web(host: str, port: int) -> None:
    """Run the FastAPI web server inside the existing event loop."""
    global _web_server
    config = uvicorn.Config(web_app, host=host, port=port, log_level="error")
    _web_server = uvicorn.Server(config)
    if _web_server is not None:
        await _web_server.serve()


async def run(config):
    """Run the daemon — start manager, load personas, start web server, heartbeat."""
    from application.platform.observer import set_loop
    set_loop(asyncio.get_running_loop())

    subscribe(on_signal)
    manager.start(web_app)

    loop = asyncio.get_running_loop()
    shutdown = asyncio.Event()
    if sys.platform == "win32":
        signal.signal(signal.SIGTERM, lambda *_: shutdown.set())
        signal.signal(signal.SIGINT, lambda *_: shutdown.set())
    else:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, shutdown.set)

    # Ensure inference engine is running
    outcome = await environment.ready()
    if not outcome.success:
        print(f"Warning: {outcome.message}")

    # For each customer, assign an agent
    outcome = await persona.get_list()
    if not outcome.success:
        print(f"No personas yet: {outcome.message}")

    personas = outcome.data.personas if outcome.data else []
    for p in personas:
        if p.status != "active":
            print(f"Skipping {p.name} ({p.status})")
            continue
        try:
            manager.serve(p)
        except Exception as e:
            print(f"Failed to serve {p.name}: {e}")

    # Open the door
    web_task = asyncio.create_task(start_web(config.host, config.port))
    web_task.add_done_callback(
        lambda t: print(f"Web server stopped: {t.exception()}") if not t.cancelled() and t.exception() else None
    )

    # Wait for shutdown — each agent runs its own heartbeat
    await shutdown.wait()

    # Graceful shutdown
    print("Shutting down...")
    await manager.release_all()

    if _web_server:
        _web_server.should_exit = True
    try:
        await asyncio.wait_for(web_task, timeout=5)
    except asyncio.TimeoutError:
        web_task.cancel()
