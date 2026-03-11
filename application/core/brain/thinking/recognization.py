"""Recognization — matches the most important unrecognized Perception to a Meaning.

Meanings are presented as a numbered list. The LLM returns the row number of
the best-matching meaning. Escalation is used as fallback if the row is missing
or out of range.
"""

from application.core.data import Prompt
from application.core.brain import perceptions
from application.core.brain.meanings import all_meanings
from application.platform import logger


async def by(reason, mind) -> None:
    perception = mind.most_important_perception
    if not perception:
        return

    persona = mind.persona
    logger.info("recognization.by", {"impression": perception.impression})

    meanings = all_meanings(persona)
    meanings_text = "\n".join(
        f"{i + 1}. {m.name}: {m.description()}" for i, m in enumerate(meanings)
    )

    system = (
        "# Task: Match a conversation thread to a meaning\n"
        "Given a numbered list of known meanings and a conversation thread, "
        "return the row number of the best-matching meaning.\n"
        "Use the Escalation row if no meaning fits.\n\n"
        "Return JSON:\n"
        '{"meaning_row": N}'
    )

    prompts = [Prompt(role="user", content=(
        f"Known meanings:\n{meanings_text}\n\n"
        f"Thread to match:\n{perceptions.thread(perception)}\n\n"
        "Return the row number of the best-matching meaning."
    ))]

    result = await reason(persona, system, prompts)
    row = result.get("meaning_row")

    escalation = next((m for m in meanings if m.name == "Escalation"), meanings[-1])
    if isinstance(row, (int, float)) and 1 <= int(row) <= len(meanings):
        meaning = meanings[int(row) - 1]
    else:
        meaning = escalation

    mind.recognize(perception, meaning)
