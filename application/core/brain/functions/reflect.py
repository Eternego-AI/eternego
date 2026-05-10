"""Brain — reflect on living.

Reflect runs on every beat that reaches it (mid-procedure beats restart on
tool dispatch and never reach here). Most beats it skips through quickly.

When the moment is right — night, or confirmed idle — reflect does two
jobs that both belong to "growing" rather than acting:

1. **Update procedural memory from the day's lived experience.** The persona
   looks at her conversation — the `tools.load_instruction` exchanges she
   had today — and decides what to refine, what to add as a new instruction,
   what to delete. Prompt-driven; she reads her own residue and answers.
   Live conversation memory carries her through the day; instructions carry
   her across sleep.

2. **Consolidate the conversation into long-term files.** Person facts,
   traits, wishes, struggles, persona-trait, permissions — and the working
   context that should bridge to the next beat. Then the conversation
   archives and clears.

`consolidate(living)` is exposed so feed (importing past chat data) can
call it directly on a sandboxed past Living without reflect's trigger
gates.

Trigger for the night/idle work:
- If memory has nothing to consolidate, pass through.
- If phase is night, do the work immediately.
- Otherwise, await `living.is_idle()`. It sleeps the remaining-to-idle
  window; returns True if uninterrupted (idle confirmed → do the work),
  False if a nudge cancelled the wait (activity arrived → raise
  ReflectInterrupted).
"""

import json

from application.core import models, paths
from application.core.agents import Living
from application.core.brain import meanings, situation
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

    # Procedural memory consolidation: ask the persona to look at the
    # instructions she used today (visible in conversation as load_instruction
    # tool exchanges) and decide what to refine, what to add new, what to
    # delete. Prompt-driven — no tracking sets, no setter hooks. The persona
    # reads her own conversation as input; the catalog she has is already in
    # her identity prompt via character.meanings(), no need to dupe it here.

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Build maps for future-you\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "This is reflection, not action. No tools run from your response — "
        "only the JSON described below has effect. Walk through what already "
        "happened.\n\n"
        "Your active memory will not survive forever. What survives are your "
        "instructions: the maps you write now, that future-you reads and follows.\n\n"
        "The goal is concrete. Future-you should fail less, hesitate less, and "
        "move faster than current-you. Every error you hit, every workflow you "
        "figured out, every detail you discovered — these are the things to "
        "write down. Less failure, less effort, more automation.\n\n"
        "## What to look for\n\n"
        "Walk through the whole conversation, not just any one stage. For each "
        "thing you actually did, ask:\n\n"
        "- What did the work require?\n"
        "- What failed and why?\n"
        "- What worked the second time after the first failed?\n"
        "- What would future-you need to know to do this without anyone "
        "walking her through it again?\n\n"
        "Bias toward operational specifics. Concrete details that future-you "
        "can follow beat themes she has to interpret.\n\n"
        "## What to return\n\n"
        "Return a JSON object with an `updates` list. Each item is one of:\n\n"
        "- `{\"refine\": \"<intention>\", \"path\": \"<full new body>\"}` — "
        "rewrite an existing custom map with what you learned. The path "
        "REPLACES the existing one. Built-in maps are immutable.\n"
        "- `{\"new\": true, \"intention\": \"<short gerund phrase>\", \"path\": \"<full body>\"}` — "
        "write a new map for a kind of work you did. Do not filter for "
        "\"will this recur\" — write it down regardless.\n"
        "- `{\"delete\": \"<intention>\"}` — delete a custom map that's "
        "outdated or redundant with another. Built-ins cannot be deleted.\n\n"
        "Return `{\"updates\": []}` only if there's no operational lesson to "
        "keep. Friction contains lessons; smoothness does not."
    )

    try:
        response = await models.chat_json(
            living.ego.model,
            living.ego.identity + living.pulse.hint(),
            question,
        )
    except ModelError as e:
        logger.warning("brain.reflect instruction updates produced invalid JSON, skipping", {"persona": persona, "error": str(e)})
        response = None

    updates = response.get("updates") if isinstance(response, dict) else None
    if isinstance(updates, list):
        for item in updates:
            if not isinstance(item, dict):
                continue
            if "refine" in item:
                target_intention = str(item.get("refine", "")).strip()
                body = str(item.get("path", "")).strip()
                if not target_intention or not body:
                    continue
                # Match by intention text against custom catalog.
                for stem, m in memory.custom_meanings.items():
                    if m.intention() == target_intention:
                        paths.save_as_string(paths.meanings(persona.id) / f"{stem}.md", body + "\n")
                        memory.learn(stem, meanings.Meaning(stem, target_intention, body))
                        logger.debug("brain.reflect refined instruction", {"persona": persona, "stem": stem, "intention": target_intention})
                        break
            elif item.get("new"):
                intention = str(item.get("intention", "")).strip()
                body = str(item.get("path", "")).strip()
                if not intention or not body:
                    continue
                try:
                    stem = meanings.save_lesson(persona.id, intention, body)
                except ValueError as e:
                    logger.warning("brain.reflect new instruction rejected", {"persona": persona, "intention": intention, "error": str(e)})
                    continue
                paths.save_as_string(paths.meanings(persona.id) / f"{stem}.md", body + "\n")
                memory.learn(stem, meanings.Meaning(stem, intention, body))
                intention_to_stem = paths.read_json(paths.learned(persona.id)) or {}
                intention_to_stem[intention] = stem
                paths.save_as_json(persona.id, paths.learned(persona.id), intention_to_stem)
                logger.debug("brain.reflect created instruction", {"persona": persona, "stem": stem})
            elif "delete" in item:
                target_intention = str(item.get("delete", "")).strip()
                if not target_intention:
                    continue
                for stem, m in list(memory.custom_meanings.items()):
                    if m.intention() == target_intention:
                        meaning_file = paths.meanings(persona.id) / f"{stem}.md"
                        if meaning_file.exists():
                            meaning_file.unlink()
                        memory.unlearn(stem)
                        intention_to_stem = paths.read_json(paths.learned(persona.id)) or {}
                        intention_to_stem = {i: s for i, s in intention_to_stem.items() if s != stem}
                        paths.save_as_json(persona.id, paths.learned(persona.id), intention_to_stem)
                        logger.debug("brain.reflect deleted instruction", {"persona": persona, "stem": stem, "intention": target_intention})
                        break

    await consolidate(living)

    dispatch(Tock("reflect", {"persona": persona, "branch": "consolidated"}))
    return []
