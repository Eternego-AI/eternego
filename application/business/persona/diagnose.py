"""Persona — full diagnostic snapshot, all from disk.

Reads three things in one pass — vital state, last-known mind, and raw
health entries — so a status page can render the whole picture without
needing the persona to be served.
"""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Persona
from application.platform import logger


@dataclass
class DiagnoseData:
    status: str
    mind: dict
    health: list[dict]


async def diagnose(persona: Persona) -> Outcome[DiagnoseData]:
    """Read the persona's status, mind, and health from disk.

    `status` is the persona's high-level vital — `active`, `sick`, or
    `hibernate` — already on the persona dataclass after `find` loads it.
    `mind` is the latest persisted mind state (messages and context); plan
    and meaning aren't carried since they're ephemeral by design. `health`
    is the raw health-check log, oldest first — shaping into a grid or
    summary belongs to whoever's looking at it.
    """
    bus.propose("Diagnosing persona", {"persona": persona})
    try:
        mind: dict = {}
        try:
            entries = paths.read_json(paths.memory(persona.id))
            if entries:
                mind = entries[0]
        except Exception as e:
            logger.warning("Could not read memory file", {"persona": persona, "error": str(e)})

        health: list[dict] = []
        try:
            health = paths.read_jsonl(paths.health_log(persona.id))
        except Exception as e:
            logger.warning("Could not read health log", {"persona": persona, "error": str(e)})

        bus.broadcast("Persona diagnosed", {"persona": persona})
        return Outcome(
            success=True,
            message="",
            data=DiagnoseData(status=persona.status, mind=mind, health=health),
        )
    except Exception as e:
        bus.broadcast("Diagnose failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
