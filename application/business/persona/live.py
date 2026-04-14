"""Persona — health check and due destiny entries."""

from application.business.outcome import Outcome
from application.core import agents, bus, paths
from application.core.data import Message, Persona
from application.core.exceptions import MindError
from application.platform import filesystem

from .recover import recover


async def live(persona: Persona, dt) -> Outcome[None]:
    """Check persona health and due destiny entries."""
    ego = agents.persona(persona)

    if ego.worker.idle and ego.worker.error:
        await recover(persona, ego.worker.error)

    await bus.propose("Checking todos", {"persona": persona})
    try:
        due = paths.due_destiny_entries(persona.id, dt)
        if not due:
            await bus.broadcast("No todos due", {"persona": persona})
            return Outcome(success=True, message="Nothing due.")

        notifications = []
        for filepath, content in due:
            paths.add_history_entry(persona.id, filepath.stem, content)
            filesystem.delete(filepath)
            notifications.append(content)

        ego.memory.add(Message(content="Due now:\n" + "\n---\n".join(notifications)))
        ego.worker.nudge()

        await bus.broadcast("Todos checked", {"persona": persona, "due": len(due)})
        return Outcome(success=True, message=f"{len(due)} entries due.")
    except MindError as e:
        await bus.broadcast("Todos check failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
