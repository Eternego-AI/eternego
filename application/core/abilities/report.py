"""Ability — report.

Speak inside a procedure. Use this from within `steps` when you are in
the middle of doing something and want to narrate progress, explain a
choice, or surface a result. Mechanically the same as `say` (the message
reaches the person, an assistant turn is added to memory), but the
intent is different: `say` ends a beat on its own; `report` is one move
among several in the same beat.

There is no waiting. After reporting, the next step in `steps` runs
immediately. If you need a response from the person, use `ask` instead.
"""

from application.core.abilities import ability
from application.platform import logger
from application.platform.observer import Command, dispatch


@ability(
    "Narrate while acting in the same beat. Pair with another action in your "
    "decision list to speak AND do in one step. After reporting, the next "
    "action in your decision list runs immediately — no waiting for a reply "
    "(use `tools.ask` for that)."
)
async def report(persona, text: str = "") -> str:
    logger.debug("ability.report", {"persona": persona, "text": text})
    if not text:
        raise ValueError("text is required")
    dispatch(Command("Persona wants to say", {"persona": persona, "text": text}))
    return "reported"
