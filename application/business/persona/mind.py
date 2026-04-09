"""Persona — reading the cognitive state of a persona."""

from application.business.outcome import Outcome
from application.core import agents, bus
from application.core.exceptions import MindError

from .loaded import loaded


async def mind(persona_id: str) -> Outcome[dict]:
    """Return the full cognitive state — signals, perceptions, thoughts, and pipeline position."""
    await bus.propose("Getting persona mind", {"persona_id": persona_id})
    result = await loaded(persona_id)
    if not result.success:
        return result
    try:
        ego = agents.persona(result.data["persona"])
        memory = ego.memory

        await bus.broadcast("Persona mind loaded", {"persona_id": persona_id})
        return Outcome(success=True, message="", data={
            "signals": [
                {"id": s.id, "event": s.event, "content": s.content, "created_at": s.created_at.isoformat()}
                for s in memory.signals
            ],
            "perceptions": [
                {"impression": p.impression, "thread": [s.id for s in p.thread]}
                for p in memory.perceptions
            ],
            "thoughts": [
                {"id": t.id, "perception": t.perception.impression, "meaning": t.meaning.name, "priority": t.priority}
                for t in memory.intentions
            ],
            "unattended": len(memory.needs_realizing),
        })
    except MindError as e:
        await bus.broadcast("Reading persona mind failed", {"persona_id": persona_id, "error": str(e)})
        return Outcome(success=False, message=str(e))
