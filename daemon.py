"""Eternego daemon — long-running process that serves personas."""

import asyncio
import signal
import sys

import uvicorn

from application.business import persona, routine
from application.core import agents
from application.platform import datetimes, logger
from application.platform.asyncio_worker import Worker
from application.platform.observer import Command, Signal, subscribe
from web.app import app as web_app
from web.socket import on_signal


_web_server: uvicorn.Server | None = None


async def start_web(host: str, port: int) -> None:
    """Run the FastAPI web server inside the existing event loop."""
    global _web_server
    config = uvicorn.Config(web_app, host=host, port=port, log_level="error")
    _web_server = uvicorn.Server(config)
    await _web_server.serve()


async def on_channel_paired(signal: Signal):
    if signal.title != "Channel paired":
        return
    persona_id = signal.details.get("persona_id")
    if not persona_id:
        return
    live = await persona.loaded(persona_id)
    if live.success:
        worker = agents.persona(live.data["persona"]).worker
        await persona.nap(live.data["persona"])
    else:
        worker = Worker()
    await persona.wake(persona_id, worker)


async def restart_gateway(command: Command):
    if command.title != "Restart gateway":
        return

    agent = command.details.get("persona")
    if not agent:
        return

    worker = agents.persona(agent).worker
    outcome = await persona.nap(agent)
    if not outcome.success:
        print(f"Failed to nap {agent.name}: {outcome.message}")
        return

    outcome = await persona.wake(agent.id, worker)
    if not outcome.success:
        print(f"Failed to wake {agent.name}: {outcome.message}")


async def run(config):
    """Run the daemon — load personas, start web server, heartbeat loop."""

    # Daemon-specific signal subscriptions
    subscribe(restart_gateway, on_channel_paired, on_signal)

    # Graceful shutdown on SIGTERM/SIGINT
    loop = asyncio.get_running_loop()
    shutdown = asyncio.Event()
    if sys.platform == "win32":
        signal.signal(signal.SIGTERM, lambda *_: shutdown.set())
        signal.signal(signal.SIGINT, lambda *_: shutdown.set())
    else:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, shutdown.set)

    # Load and wake all personas
    outcome = await persona.get_list()
    if not outcome.success:
        print(f"No personas yet: {outcome.message}")

    personas = (outcome.data or {}).get("personas", [])
    for agent in personas:
        outcome = await persona.wake(agent.id, Worker())
        if not outcome.success:
            print(f"Failed to wake {agent.name}: {outcome.message}")

    # Start web server
    web_task = asyncio.create_task(start_web(config.host, config.port))
    web_task.add_done_callback(
        lambda t: print(f"Web server stopped: {t.exception()}") if not t.cancelled() and t.exception() else None
    )

    # Heartbeat loop
    elapsed = 0
    while not shutdown.is_set():
        try:
            await asyncio.wait_for(shutdown.wait(), timeout=1)
        except asyncio.TimeoutError:
            pass
        elapsed += 1
        if elapsed >= 60:
            elapsed = 0
            outcome = await persona.running()
            if outcome.success:
                for agent in (outcome.data or {}).get("personas", []):
                    now = datetimes.now()
                    logger.info("Heartbeat", {"persona": agent.id, "time": now.strftime("%Y-%m-%d %H:%M")})
                    await persona.live(agent, now)
                    await routine.trigger(agent)

    # Graceful shutdown
    print("Shutting down...")
    outcome = await persona.running()
    if outcome.success:
        for agent in (outcome.data or {}).get("personas", []):
            await persona.nap(agent)

    if _web_server:
        _web_server.should_exit = True
    try:
        await asyncio.wait_for(web_task, timeout=5)
    except asyncio.TimeoutError:
        web_task.cancel()
