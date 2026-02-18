"""Eternego service — entry point for running all persona gateways."""

import argparse
import asyncio

from application.business import persona
from application.platform import logger
from application.platform.observer import Command, Event, Plan, Signal, subscribe

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
    subscribe(log_signal, restart_gateway)

    outcome = await persona.agents()
    if not outcome.success:
        print(f"Failed to load personas: {outcome.message}")
        return

    personas = (outcome.data or {}).get("personas", [])
    if not personas:
        print("No personas found. Create one first.")
        return

    for agent in personas:
        outcome = await persona.start(agent)
        if not outcome.success:
            print(f"Failed to start gateway for {agent.name}: {outcome.message}")

    # Keep the event loop alive for signal handling and on_message callbacks
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
