"""Eternego service — entry point for running all persona gateways."""

import asyncio

from application.business import persona
from application.platform import logger
from application.platform.observer import Command, Event, Plan, subscribe


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


def log_signal(signal: Event | Plan):
    print(f"[{signal.__class__.__name__}] {signal.title}", signal.details)
    logger.info(signal.title, signal.details)


async def main():
    logger.default_media(logger.file_media("eternego.log"))
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
