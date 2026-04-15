"""Brain — reflect stage."""

from application.core import models
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Persona, Prompt
from application.platform import logger


async def reflect(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.reflect", {"persona": persona, "messages": memory.messages, "context": memory.context})
    try:
        existing = (memory.context or "").strip() or "(nothing yet)"
        system = (
            identity
            + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "# ▶ YOUR TASK: Close this cycle — summarize reality and choose what to carry forward\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "This tick is ending. Look across the conversation that follows and summarize what "
            "actually happened — what was asked, what you did, what you said, what is resolved, "
            "what is left open.\n\n"
            "Then decide whether something is genuinely worth continuing right now. If there is a "
            "thread in front of you — a task you started and did not finish, a follow-up you owe, "
            "a wish or struggle you can keep moving toward — and you can meaningfully take one "
            "more step on it now, name it as a leftover. If nothing calls for another step, leave "
            "the leftover empty; silence is an honest answer.\n\n"
            "## Previous context\n\n"
            f"{existing}\n\n"
            "## Output\n\n"
            "Return JSON with two fields:\n"
            "- `context`: the FULL updated operational summary. Keep every previous line still "
            "relevant; drop items resolved in this tick, or `[in_progress]` / `[pending_followup]` "
            "items superseded by a new `[decided]`; add new items. If the list exceeds 30 lines, "
            "drop the oldest `[discussed]` lines first. If nothing changed, return the previous "
            "context byte-for-byte. Lines are one per entry, each beginning with a tag:\n"
            "  - `[discussed] <topic>`\n"
            "  - `[decided] <decision>`\n"
            "  - `[in_progress] <work item>`\n"
            "  - `[committed] <commitment by person or you>`\n"
            "  - `[pending_followup] <what is waiting on whom>`\n"
            "  - `[reason] <reason behind a recent decision>`\n"
            "- `leftover`: a single short sentence describing the one thing worth continuing right "
            "now, or `\"\"` if nothing calls for another step.\n\n"
            "```json\n"
            "{\"context\": \"...\",\n"
            " \"leftover\": \"\"}\n"
            "```"
        )
        result = await models.chat_json(persona.thinking, [{"role": "system", "content": system}] + memory.prompts)
        if not isinstance(result, dict):
            return False

        context = str(result.get("context", "")).strip()
        leftover = str(result.get("leftover", "")).strip()

        if context:
            memory.context = context
        logger.debug("brain.reflect result", {"persona": persona, "context": memory.context, "leftover": leftover})
        memory.clear()

        if leftover:
            seed_text = f"Return to: {leftover}"
            memory.add(Message(
                content=seed_text,
                prompt=Prompt(role="user", content=seed_text),
            ))
            return False

        return True
    except Exception as e:
        logger.warning("brain.reflect failed", {"persona": persona, "error": str(e)})
        return False
