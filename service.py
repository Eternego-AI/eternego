"""Eternego service — entry point for running all persona gateways."""

import argparse
import asyncio

import uvicorn

from application.business import persona
from application.platform import logger
from config import web as web_config
from config.application import log_file, signal_log_file
import heart
from application.platform.observer import Command, Event, Plan, Signal, subscribe
from web.app import app as web_app
from web.socket import on_signal


async def start_web(host: str, port: int) -> None:
    """Run the FastAPI web server inside the existing event loop."""
    config = uvicorn.Config(web_app, host=host, port=port, log_level="warning")
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
        await persona.stop(live.data["persona"])
    outcome = await persona.find(persona_id)
    if outcome.success:
        await persona.start(outcome.data["persona"])


async def restart_gateway(command: Command):
    if command.title != "Restart gateway":
        return

    agent = command.details.get("persona")
    if not agent:
        return

    outcome = await persona.stop(agent)
    if not outcome.success:
        print(f"Failed to stop gateway for {agent.name}: {outcome.message}")
        return

    outcome = await persona.start(agent)
    if not outcome.success:
        print(f"Failed to start gateway for {agent.name}: {outcome.message}")


async def main():
    parser = argparse.ArgumentParser(description="Eternego service")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("--port", type=int, default=web_config.PORT, help=f"Web server port (default: {web_config.PORT})")
    parser.add_argument("--host", default=web_config.HOST, help=f"Web server host (default: {web_config.HOST})")
    args = parser.parse_args()
    verbosity = args.verbose

    levels = list(logger.Level)
    info_index = levels.index(logger.Level.INFO)

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

    outcome = await persona.agents()
    if not outcome.success:
        print(f"Failed to load personas: {outcome.message}")
        return

    personas = (outcome.data or {}).get("personas", [])

    for agent in personas:
        outcome = await persona.start(agent)
        if not outcome.success:
            print(f"Failed to start gateway for {agent.name}: {outcome.message}")

    web_task = asyncio.create_task(start_web(args.host, args.port))
    web_task.add_done_callback(
        lambda t: print(f"Web server stopped: {t.exception()}") if not t.cancelled() and t.exception() else None
    )

    elapsed = 0
    while True:
        await asyncio.sleep(1)
        elapsed += 1
        if elapsed >= 60:
            elapsed = 0
            outcome = await persona.running()
            if outcome.success:
                for agent in (outcome.data or {}).get("personas", []):
                    await heart.beat(agent)


if __name__ == "__main__":
    asyncio.run(main())
