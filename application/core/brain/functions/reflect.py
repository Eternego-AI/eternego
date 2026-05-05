"""Brain — reflect on living.

The single sleep-time function for text-side memory consolidation. Replaces
the old reflect (per-tick context update) and the old transform (night-time
distillation): one stage, one model call, one shared decision about what to
keep.

Reflect itself is the trigger: it fires `consolidate(living)` only when the
moment calls for it. `consolidate` is exposed so feed (importing past chat
data) can call it directly on a sandboxed past Living without going through
reflect's trigger gates.

Trigger:
- If memory has nothing to consolidate, pass through.
- If phase is night, consolidate immediately.
- Otherwise, await `living.is_idle()`. It sleeps the remaining-to-idle window;
  returns True if uninterrupted (idle confirmed → consolidate), False if a
  nudge cancelled the wait (activity arrived → skip this beat).

The persona reads its conversation as data inside a single user message and
decides what to keep going forward — a new context (its carried internal
narrative) and updated person files (identity, traits, wishes, struggles,
persona-traits, permissions). What it says replaces what it currently has.

Order after the model returns: write person files → set context → archive
messages and forget. Most fail-prone work first: if file writes fail, nothing
changed and the next call retries cleanly.
"""

import json

from application.core import models, paths
from application.core.agents import Living
from application.core.brain import situation
from application.core.brain.pulse import Phase
from application.core.brain.signals import Tick, Tock
from application.core.exceptions import ModelError, ReflectInterrupted
from application.platform import logger
from application.platform.observer import dispatch


async def consolidate(living: Living) -> bool:
    """Distill the conversation in `living.ego.memory` into context + person
    files, then archive messages and forget. No trigger checks, no Tick/Tock
    dispatch — pure work.

    Returns True if consolidation happened, False if there was nothing to do
    or the model failed."""
    persona = living.ego.persona
    memory = living.ego.memory

    if not memory.messages:
        return False

    conversation = []
    for m in memory.messages:
        if not m.prompt:
            continue
        content = m.prompt.content
        if isinstance(content, list):
            content = "[multimodal]"
        conversation.append({"role": m.prompt.role, "content": content})

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: What do you want to keep?\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{situation.time()}\n\n"
        "Here is the conversation that happened:\n\n"
        "```json\n"
        f"{json.dumps(conversation, ensure_ascii=False, indent=2)}\n"
        "```\n\n"
        "You're closing this stretch. Walk back through the conversation and decide what to keep.\n\n"
        "What you keep splits into two kinds of memory.\n\n"
        "## Long-term — your stable knowledge\n\n"
        "Each of these is a file you carry across days and weeks. Each holds one kind of thing. Whatever you say here REPLACES what you currently have — so if a fact emerged from today, fold it in; if nothing changed, return what's there exactly.\n\n"
        "- `identity` — facts about the person that don't change often: name, where they live, who's in their life, work, age, addresses. The kind of thing someone tells you once.\n"
        "- `traits` — how they behave. Communication style, decision patterns, what they react to, the texture of their thinking. Stable; evolves slowly as you learn them.\n"
        "- `wishes` — what they reach for. Long-term goals, aspirations, what they're trying to build or move toward. Strategic, not daily.\n"
        "- `struggles` — what holds them back. Recurring patterns of difficulty, places they get stuck. Stable shapes, not today's frustration.\n"
        "- `persona_traits` — how they want you to be with them. Your tone, what's worked between you. Stable.\n"
        "- `permissions` — what they've granted you and what they haven't. The boundary of your agency. Updates only on explicit grants, takes, or refusals.\n\n"
        "## Short-term — your context\n\n"
        "This is your WORKING memory: what you're carrying across loops right now that isn't a stable fact. The thread you're following. The decisions you're holding mid-flight. What you'd brief your next loop on so nothing drops. For now or today — not for forever.\n\n"
        "Anything that belongs in the long-term files goes there, not here. Context is what's left: what's active, what's in motion, what you don't want to lose between this loop and the next.\n\n"
        "Keep it short. A few sentences in your own voice. If nothing's actively in flight, return an empty string — that's honest, better than padding.\n\n"
        "## Output\n\n"
        "Return a JSON object with these fields. Lists capped at 7 items where it matters; lists may be empty.\n\n"
        "```json\n"
        "{\"context\": \"<short prose, your working memory>\",\n"
        " \"identity\": [\"<fact>\", \"<fact>\"],\n"
        " \"traits\": [\"<item>\", \"<item>\"],\n"
        " \"wishes\": [\"<item>\", \"<item>\"],\n"
        " \"struggles\": [\"<item>\", \"<item>\"],\n"
        " \"persona_traits\": [\"<item>\", \"<item>\"],\n"
        " \"permissions\": [\"<item>\", \"<item>\"]}\n"
        "```"
    )

    try:
        result = await models.chat_json(living.ego.model, living.ego.identity + living.pulse.hint(), question)
    except ModelError as e:
        logger.warning("brain.consolidate produced invalid JSON, will retry next consolidation", {"persona": persona, "error": str(e)})
        return False

    if not isinstance(result, dict):
        return False

    def to_lines(value):
        if isinstance(value, list):
            return "\n".join(f"- {item}" for item in value if item)
        return str(value).strip()

    paths.save_as_string(paths.person_identity(persona.id), to_lines(result.get("identity", "")))
    paths.save_as_string(paths.person_traits(persona.id), to_lines(result.get("traits", "")))
    paths.save_as_string(paths.wishes(persona.id), to_lines(result.get("wishes", "")))
    paths.save_as_string(paths.struggles(persona.id), to_lines(result.get("struggles", "")))
    paths.save_as_string(paths.persona_trait(persona.id), to_lines(result.get("persona_traits", "")))
    paths.save_as_string(paths.permissions(persona.id), to_lines(result.get("permissions", "")))

    new_context = str(result.get("context", "")).strip()
    if new_context:
        memory.context = new_context

    memory.archive_messages()
    memory.forget()

    return True


async def reflect(living: Living) -> list:
    """reflect ON living — look back upon what was."""
    dispatch(Tick("reflect", {"persona": living.ego.persona}))

    persona = living.ego.persona
    memory = living.ego.memory
    logger.debug("brain.reflect", {"persona": persona, "messages_count": len(memory.messages)})

    if not memory.messages:
        dispatch(Tock("reflect", {"persona": persona, "branch": "no-messages"}))
        return []

    if living.pulse.phase != Phase.NIGHT:
        if not await living.is_idle():
            dispatch(Tock("reflect", {"persona": persona, "branch": "not-idle"}))
            raise ReflectInterrupted()

    await consolidate(living)

    dispatch(Tock("reflect", {"persona": persona, "branch": "consolidated"}))
    return []
