"""Persona — recovering from a failure."""

from application.business.outcome import Outcome
from application.core import agents, bus, channels, paths
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import FrontierError, MindError
from application.platform import datetimes


async def recover(persona: Persona, error: Exception) -> Outcome[None]:
    """It lets the persona recover from a failure — acknowledge what happened, restart, and carry on."""
    await bus.propose("Recovering persona", {"persona": persona, "error": str(error)})

    try:
        ego = agents.persona(persona)

        if isinstance(error, FrontierError):
            text = "I tried to reach out to my mentor but they weren't around. Give me a moment to try again."
        else:
            text = "Sorry, it seems I got distracted. Let me see what I should be doing."

        ego.memory.add(Message(
            content=text,
            prompt=Prompt(role="assistant", content=text),
        ))
        paths.append_jsonl(paths.conversation(persona.id), {
            "role": "persona",
            "content": text,
            "channel": "",
            "time": datetimes.iso_8601(datetimes.now()),
        })
        await channels.send_all(persona, text)
        ego.worker.reset()
        ego.worker.nudge()

        await bus.broadcast("Persona recovered", {"persona": persona, "error": str(error)})
        return Outcome(success=True, message="Persona recovered.")

    except MindError as e:
        await bus.broadcast("Persona recovery failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not recover persona.")
