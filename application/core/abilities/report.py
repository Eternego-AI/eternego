"""Ability — report.

Speak in the same beat as an action. Use this when you are doing
something and want to surface a result or explain a choice alongside
the action. Mechanically the same as `say` (the message reaches the
person, an assistant turn is added to memory), but the intent is
different: `say` ends a beat on its own; `report` is one move among
several in the same beat.

There is no waiting. After reporting, the next step in the decision
list runs immediately. If you need a response from the person, use
`ask` instead.
"""

from application.core.abilities import ability
from application.platform import logger
from application.platform.observer import Command, dispatch


@ability(
    "Speak alongside another action in the same beat — pair with another "
    "action in your decision list. The next action runs immediately, no "
    "waiting for a reply (use `tools.ask` for that). Don't use alone — that's "
    "just `say` with extra wrapping."
)
async def report(persona, text: str = "") -> str:
    logger.debug("ability.report", {"persona": persona, "text": text})
    if not text:
        raise ValueError("text is required")
    dispatch(Command("Persona wants to say", {"persona": persona, "text": text}))
    return "reported"
