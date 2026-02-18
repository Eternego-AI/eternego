"""Eternego service — entry point for running all persona gateways."""

import argparse
import asyncio

import uvicorn

from application.business import persona
from application.platform import logger
from application.platform.observer import Command, Event, Plan, Signal, subscribe
from web.app import app as web_app
from web.socket import on_signal


async def start_web(host: str, port: int) -> None:
    """Run the FastAPI web server inside the existing event loop."""
    config = uvicorn.Config(web_app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def predict_loop(personas: list, interval: int) -> None:
    """Run predict for every persona with an active channel on a fixed interval."""
    while True:
        await asyncio.sleep(interval)
        for agent in personas:
            if not (agent.channels or []):
                continue
            channel = agent.channels[0]
            outcome = await persona.predict(agent, channel)
            if not outcome.success:
                logger.warning(f"Predict failed for {agent.name}", {"reason": outcome.message})


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
    parser.add_argument("--predict-interval", type=int, default=60, metavar="SECONDS",
                        help="How often to run predict for each persona (default: 60, 0 to disable)")
    parser.add_argument("--port", type=int, default=5001, help="Web server port (default: 5001)")
    parser.add_argument("--host", default="127.0.0.1", help="Web server host (default: 127.0.0.1)")
    args = parser.parse_args()
    verbosity = args.verbose

    levels = list(logger.Level)
    info_index = levels.index(logger.Level.INFO)

    file_log = logger.file_media("eternego.log")
    def log_media(message):
        file_log(message)
        if verbosity >= 3 or (verbosity >= 2 and levels.index(message.level) <= info_index):
            print(f"[{message.level.value}] {message.title}", message.context)

    file_signal = logger.file_media("eternego-signals.log")
    def signal_media(message):
        file_signal(message)

    def log_signal(signal: Signal):
        logger.info(signal.title, signal.details, signal_media)
        if verbosity >= 2 or (verbosity >= 1 and isinstance(signal, (Plan, Event))):
            print(f"[{signal.__class__.__name__}] {signal.title}", signal.details)

    logger.default_media(log_media)
    subscribe(log_signal, restart_gateway, on_signal)

    outcome = await persona.agents()
    if not outcome.success:
        print(f"Failed to load personas: {outcome.message}")
        return

    personas = (outcome.data or {}).get("personas", [])

    for agent in personas:
        outcome = await persona.start(agent)
        if not outcome.success:
            print(f"Failed to start gateway for {agent.name}: {outcome.message}")

    if personas and args.predict_interval > 0:
        asyncio.create_task(predict_loop(personas, args.predict_interval))

    web_task = asyncio.create_task(start_web(args.host, args.port))
    web_task.add_done_callback(
        lambda t: print(f"Web server stopped: {t.exception()}") if not t.cancelled() and t.exception() else None
    )

    # Keep the event loop alive for signal handling and on_message callbacks
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
