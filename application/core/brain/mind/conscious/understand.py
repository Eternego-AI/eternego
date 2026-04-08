"""Conscious — match perceptions to meanings."""

from application.core.brain import perceptions
from application.core import bus, models
from application.platform import logger


async def understand(memory, persona, meanings, identity_fn, escalate_fn, express_thinking_fn) -> None:
    """Match the most important unrecognized perception to a meaning."""
    perception = memory.most_important_perception
    if not perception:
        return

    logger.debug("Understand", {"persona": persona, "impression": perception.impression})
    await bus.share("Pipeline: understand", {"persona": persona, "stage": "understand", "impression": perception.impression})

    await express_thinking_fn()

    meanings_text = "\n".join(
        f"{i + 1}. {m.name}: {m.description()}"
        for i, m in enumerate(meanings)
    )

    system = (
        identity_fn()
        + "\n\n# Task: Match a conversation thread to a meaning\n"
        "Given a numbered list of known meanings and a conversation thread, "
        "return the row number of the best-matching meaning.\n"
        "Use the Escalation row if no meaning fits.\n\n"
        "Return JSON:\n"
        '{"meaning_row": N}\n\n'
        f"Known meanings:\n{meanings_text}\n\n"
        "Return the row number of the best-matching meaning."
    )

    messages = [{"role": "system", "content": system}] + perceptions.to_conversation(perception.thread)
    result = await models.chat_json_stream(persona.thinking, messages)
    row = result.get("meaning_row")

    escalation = next(m for m in meanings if m.name == "Escalation")
    if isinstance(row, (int, float)) and 1 <= int(row) <= len(meanings):
        meaning = meanings[int(row) - 1]
    else:
        meaning = escalation

    # Escalation -> try generating a new meaning via frontier/local model
    if meaning.name == "Escalation":
        from application.core.brain.mind import meanings as meanings_module
        code = await escalate_fn(perceptions.thread(perception), meanings)
        if code:
            try:
                new_meaning = meanings_module.learn(persona, code)
                meanings.append(new_meaning)
                meaning = new_meaning
            except Exception as e:
                logger.error("understand: failed to learn meaning", {"persona": persona, "error": str(e)})

    memory.understand(perception, meaning)
