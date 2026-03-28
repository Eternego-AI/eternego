"""Eternego service — entry point for running all persona gateways."""

import argparse
import asyncio
import signal

import uvicorn

from application.business import persona
from application.core import agents
from application.platform import logger
from application.platform.asyncio_worker import Worker
from config import web as web_config
from config.application import log_file, signal_log_file
import heart
from application.platform.observer import Command, Event, Plan, Signal, subscribe
from web.app import app as web_app
from web.socket import on_signal


async def start_web(host: str, port: int) -> None:
    """Run the FastAPI web server inside the existing event loop."""
    config = uvicorn.Config(web_app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    await server.serve()


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


async def main():
    parser = argparse.ArgumentParser(description="Eternego service")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("--port", type=int, default=web_config.PORT, help=f"Web server port (default: {web_config.PORT})")
    parser.add_argument("--host", default=web_config.HOST, help=f"Web server host (default: {web_config.HOST})")
    args = parser.parse_args()
    verbosity = args.verbose

    levels = list(logger.Level)
    info_index = levels.index(logger.Level.INFO)

    log_file().parent.mkdir(parents=True, exist_ok=True)  # Windows needs this upfront
    file_log = logger.file_media(log_file)
    def log_media(message):
        file_log(message)
        if verbosity >= 3 or (verbosity >= 2 and levels.index(message.level) <= info_index):
            print(f"[{message.level.value}] {message.title}", message.context)

    file_signal = logger.file_media(signal_log_file)
    def signal_media(message):
        file_signal(message)

    def log_signal(signal: Signal):
        logger.info(signal.title, {"_type": signal.__class__.__name__, **signal.details}, signal_media)
        if verbosity >= 2 or (verbosity >= 1 and isinstance(signal, (Plan, Event))):
            print(f"[{signal.__class__.__name__}] {signal.title}", signal.details)

    logger.default_media(log_media)
    subscribe(log_signal, restart_gateway, on_channel_paired, on_signal)

    loop = asyncio.get_running_loop()
    shutdown = asyncio.Event()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown.set)

    outcome = await persona.get_list()
    if not outcome.success:
        print(f"No personas yet: {outcome.message}")

    personas = (outcome.data or {}).get("personas", [])

    for agent in personas:
        outcome = await persona.wake(agent.id, Worker())
        if not outcome.success:
            print(f"Failed to wake {agent.name}: {outcome.message}")

    web_task = asyncio.create_task(start_web(args.host, args.port))
    web_task.add_done_callback(
        lambda t: print(f"Web server stopped: {t.exception()}") if not t.cancelled() and t.exception() else None
    )

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
                    await heart.beat(agent)

    print("Shutting down...")
    outcome = await persona.running()
    if outcome.success:
        for agent in (outcome.data or {}).get("personas", []):
            await persona.nap(agent)

    web_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
