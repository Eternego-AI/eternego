"""Clock — the persona's sense of time. Using each tick, life manifests."""

import asyncio

from application.platform import logger
from application.core.brain.thinking import understanding, recognition, wondering, deciding, concluding


async def tick(mind) -> None:
    """Loop over thinking states indefinitely, restarting when mind receives new signals."""
    from application.core.brain import ego

    pipeline = [
        (understanding, ego.reason),
        (recognition,   ego.reason),
        (wondering,     ego.reply),
        (deciding,      ego.reason),
        (concluding,    ego.reply),
    ]

    logger.info("clock.tick: started", {"persona": mind.persona.id})

    while True:
        try:
            restart = False
            for state, fn in pipeline:
                await state.by(fn, mind)
                if mind.changed():
                    restart = True
                    break
            mind.persist()
            if not restart:
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.error("clock.tick: exception", {"error": str(e), "persona": mind.persona.id})
