"""Persona — periodic health check: recover from errors, process due destiny entries."""

from application.business.outcome import Outcome
from application.core import bus, channels, paths
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import FrontierError
from application.platform import datetimes, filesystem, logger


async def health_check(persona: Persona, dt) -> Outcome[None]:
    """Check worker health, recover if needed, process due destiny entries."""
    bus.propose("Health check", {"persona": persona})
    ego = persona.ego

    if ego.worker.idle and ego.worker.error:
        error = ego.worker.error
        logger.info("Recovering ego", {"persona": persona, "error": str(error)})

        if isinstance(error, FrontierError):
            text = "I tried to reach out to my mentor but they weren't around. Give me a moment to try again."
        else:
            text = "Sorry, it seems I got distracted. Let me see what I should be doing."

        ego.memory.add(Message(content=text, prompt=Prompt(role="assistant", content=text)))
        paths.append_jsonl(paths.conversation(persona.id), {
            "role": "persona",
            "content": text,
            "channel": "",
            "time": datetimes.iso_8601(datetimes.now()),
        })
        await channels.send_all(ego.channels, text)
        ego.worker.reset()
        ego.worker.nudge()

    try:
        due = paths.due_destiny_entries(persona.id, dt)
        if due:
            notifications = []
            for filepath, content in due:
                paths.add_history_entry(persona.id, filepath.stem, content)
                filesystem.delete(filepath)
                notifications.append(content)
            ego.memory.add(Message(content="Due now:\n" + "\n---\n".join(notifications)))
            ego.worker.nudge()

        bus.broadcast("Health checked", {"persona": persona})
        return Outcome(success=True, message="")
    except Exception as e:
        bus.broadcast("Health check failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
