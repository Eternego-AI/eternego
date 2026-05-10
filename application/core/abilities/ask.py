"""Ability — ask.

Send a question to the person and signal that the persona is waiting for
their response. Internally this is the same dispatch as `say` (the message
reaches the person and an assistant prompt is added to memory by the
manager) — the difference is the TOOL_RESULT, which carries `waiting for
the person's response`. The model reads that residue on its next beat and
understands not to keep retrying or moving on.

There is no system-level timeout. The persona stays in waiting only as long
as her own cognition reads the TOOL_RESULT and decides to rest. If she
chooses to follow up or pivot, that is hers to decide.
"""

from application.core.abilities import ability
from application.platform import logger
from application.platform.observer import Command, dispatch


@ability("Ask the person a question and wait for their response. Sends the message and signals that you are waiting; on your next beat you will see a TOOL_RESULT noting the wait.")
async def ask(persona, text: str = "") -> str:
    logger.debug("ability.ask", {"persona": persona, "text": text})
    if not text:
        raise ValueError("text is required")
    dispatch(Command("Persona wants to say", {"persona": persona, "text": text}))
    return "waiting for the person's response"
