"""Clock — the persona's sense of time. Using each tick, life manifests."""

import asyncio

from application.platform import logger
from application.core.brain.mind import conscious


async def tick(mind) -> None:
    """Loop over conscious thinking states indefinitely, restarting when mind receives new signals."""
    from application.core.brain import ego

    pipeline = [
        (conscious.understand, ego.reason),
        (conscious.recognize,  ego.reason),
        (conscious.wonder,     ego.reply),
        (conscious.decide,     ego.reason),
        (conscious.conclude,   ego.reply),
    ]

    logger.info("clock.tick: started", {"persona": mind.persona.id})

    while True:
        try:
            restart = False
            for step, fn in pipeline:
                await step(fn, mind)
                if mind.changed():
                    restart = True
                    break
            mind.persist()
            if not restart:
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.error("clock.tick: exception", {"error": str(e), "persona": mind.persona.id})
