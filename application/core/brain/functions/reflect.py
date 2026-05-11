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
import uuid

from application.core import models, paths
from application.core.agents import Living
from application.core.brain import meanings, situation
from application.core.brain.pulse import Phase
from application.core.brain.signals import Tick, Tock
from application.core.data import Action
from application.core.exceptions import ModelError, ReflectInterrupted
from application.platform import logger
from application.platform.observer import dispatch


CONSOLIDATING = Action(
    name="consolidating",
    description="The persona's long-term knowledge after this stretch — all fields required, each one re-emitted whether changed or unchanged.",
    fields=[
        Action(name="context",        type="string", required=True),
        Action(name="identity",       type="string", required=True),
        Action(name="traits",         type="string", required=True),
        Action(name="wishes",         type="string", required=True),
        Action(name="struggles",      type="string", required=True),
        Action(name="persona_traits", type="string", required=True),
        Action(name="permissions",    type="string", required=True),
    ],
)


EXTRACTING = Action(
    name="extracting",
    description="The procedural-memory updates from today's lived experience — refine, new, or delete maps for kinds of moments.",
    fields=[
        Action(
            name="updates",
            type="array",
            required=True,
            items=Action(
                one_of=True,
                fields=[
                    Action(
                        name="refine",
                        type="object",
                        description="rewrite an existing custom map with what you learned (built-ins are immutable)",
                        fields=[
                            Action(name="intention", type="string", required=True),
                            Action(name="path", type="string", required=True),
                        ],
                    ),
                    Action(
                        name="new",
                        type="object",
                        description="write a new map for a kind of work you did",
                        fields=[
                            Action(name="intention", type="string", required=True),
                            Action(name="path", type="string", required=True),
                        ],
                    ),
                    Action(
                        name="delete",
                        type="object",
                        description="delete a custom map that's outdated or redundant",
                        fields=[Action(name="intention", type="string", required=True)],
                    ),
                ],
            ),
        ),
    ],
)


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
        "You're closing this stretch. You already hold these files. Walk back through what they say and through what happened today; decide what should still be true tomorrow.\n\n"
        "You are curating, not stacking. Every line earns its place by changing how future-you acts — if removing it changes nothing, cut it. If today gave you something sharper than what's there, replace; don't append. If nothing changed in an area, return what's there exactly.\n\n"
        "What you keep splits into two kinds of memory.\n\n"
        "## Long-term — your stable knowledge\n\n"
        "Each of these is a file you carry across days and weeks. Each holds one focused kind of thing. Whatever you say here REPLACES what you currently have.\n\n"
        "For the interpretive fields (`traits`, `wishes`, `struggles`, `persona_traits`), write your *understanding* of the area in your own voice — synthesized, the way you'd describe them to someone who asked. Not a catalog of incidents. For factual fields (`identity`, `permissions`), keep them as discrete facts.\n\n"
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
        "Return a JSON object with these fields — every field is a string in your own voice. Markdown is fine: use bullets, sections, or short paragraphs as fits each area. No item cap — every line you keep is one future-you reads on every beat, so each one must matter. An empty string is honest when there's nothing for that area.\n\n"
        "```json\n"
        "{\"context\": \"<short prose, your working memory>\",\n"
        " \"identity\": \"<discrete facts about the person — markdown bullets work well>\",\n"
        " \"traits\": \"<your understanding of how they behave — synthesized prose>\",\n"
        " \"wishes\": \"<what they reach for — prose>\",\n"
        " \"struggles\": \"<what holds them back — prose>\",\n"
        " \"persona_traits\": \"<how they want you to be with them — prose>\",\n"
        " \"permissions\": \"<what they've granted and withheld — discrete, markdown bullets>\"}\n"
        "```"
    )

    try:
        result = await models.tool(living.ego.model, living.ego.identity + living.pulse.hint(), question, CONSOLIDATING)
    except ModelError as e:
        logger.warning("brain.consolidate produced invalid JSON, will retry next consolidation", {"persona": persona, "error": str(e)})
        return False

    if result is None:
        # Model gave up (empty {}). Preserve all files; do not consolidate.
        logger.warning("brain.consolidate model returned empty, preserving files", {"persona": persona})
        return False

    if not isinstance(result, dict):
        return False

    def to_lines(value):
        if isinstance(value, list):
            return "\n".join(f"- {item}" for item in value if item)
        return str(value).strip()

    # Per-field presence check: only write fields the model actually returned.
    # Missing field = model chose not to update that area = preserve current file.
    # `{"identity": ""}` is a deliberate wipe — respected. Missing `identity` is not.
    if "identity" in result:
        paths.save_as_string(paths.person_identity(persona.id), to_lines(result["identity"]))
    if "traits" in result:
        paths.save_as_string(paths.person_traits(persona.id), to_lines(result["traits"]))
    if "wishes" in result:
        paths.save_as_string(paths.wishes(persona.id), to_lines(result["wishes"]))
    if "struggles" in result:
        paths.save_as_string(paths.struggles(persona.id), to_lines(result["struggles"]))
    if "persona_traits" in result:
        paths.save_as_string(paths.persona_trait(persona.id), to_lines(result["persona_traits"]))
    if "permissions" in result:
        paths.save_as_string(paths.permissions(persona.id), to_lines(result["permissions"]))

    if "context" in result:
        new_context = str(result["context"]).strip()
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

    # Morning is for waking and starting, not for reflection. Reflect runs
    # during NIGHT (consolidating the day) or when the persona is idle
    # during DAY (a natural pause). Never during MORNING.
    if living.pulse.phase == Phase.MORNING:
        dispatch(Tock("reflect", {"persona": persona, "branch": "morning-skip"}))
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
        "Return a JSON object with an `updates` list. Each item is exactly one of:\n\n"
        "- `{\"refine\": {\"intention\": \"<existing intention>\", \"path\": \"<full new body>\"}}` — "
        "rewrite an existing custom map with what you learned. The path "
        "REPLACES the existing one. Built-in maps are immutable.\n"
        "- `{\"new\": {\"intention\": \"<short natural-English description, sentence case>\", \"path\": \"<full body>\"}}` — "
        "write a new map for a kind of work you did. The intention names the "
        "kind of moment in plain readable English (like the built-in entries "
        "above), not snake_case or an identifier. Do not filter for "
        "\"will this recur\" — write it down regardless.\n"
        "- `{\"delete\": {\"intention\": \"<existing intention>\"}}` — delete a custom map "
        "that's outdated or redundant with another. Built-ins cannot be deleted.\n\n"
        "Return `{\"updates\": []}` only if there's no operational lesson to "
        "keep. Friction contains lessons; smoothness does not."
    )

    try:
        response = await models.tool(
            living.ego.model,
            living.ego.identity + living.pulse.hint(),
            question,
            EXTRACTING,
        )
    except ModelError as e:
        logger.warning("brain.reflect instruction updates produced invalid JSON, skipping", {"persona": persona, "error": str(e)})
        response = None

    updates = response.get("updates") if isinstance(response, dict) else None
    if isinstance(updates, list):
        # Read the catalog once; mutate in-memory across all updates; write
        # back at the end if anything changed. The persona reads intention
        # text from her catalog and emits it back verbatim — exact match
        # here, no normalization.
        catalog = paths.read_json(paths.learned(persona.id)) or {}
        if not isinstance(catalog, dict):
            catalog = {}
        catalog_dirty = False

        for item in updates:
            if not isinstance(item, dict):
                continue
            refine = item.get("refine")
            new = item.get("new")
            delete = item.get("delete")
            if isinstance(refine, dict):
                target_intention = str(refine.get("intention", "")).strip()
                body = str(refine.get("path", "")).strip()
                if not target_intention or not body:
                    continue
                file_id = catalog.get(target_intention)
                if not file_id:
                    logger.debug("brain.reflect refine no match", {"persona": persona, "intention": target_intention})
                    continue
                paths.save_as_string(paths.meanings(persona.id) / f"{file_id}.md", body + "\n")
                memory.learn(file_id, meanings.Meaning(file_id, target_intention, body))
                logger.debug("brain.reflect refined instruction", {"persona": persona, "file_id": file_id, "intention": target_intention})
            elif isinstance(new, dict):
                intention = str(new.get("intention", "")).strip()
                body = str(new.get("path", "")).strip()
                if not intention or not body:
                    continue
                existing = catalog.get(intention)
                if existing:
                    # Intention already exists — treat as refine, update the
                    # existing file rather than orphaning it under a fresh UUID.
                    paths.save_as_string(paths.meanings(persona.id) / f"{existing}.md", body + "\n")
                    memory.learn(existing, meanings.Meaning(existing, intention, body))
                    logger.debug("brain.reflect updated existing instruction from new", {"persona": persona, "file_id": existing, "intention": intention})
                    continue
                # Generate an opaque UUID for the meaning file. Persona-
                # authored procedures don't have a separate teacher-lesson
                # form, so we write only to meanings/ (not lessons/).
                file_id = str(uuid.uuid4())
                paths.save_as_string(paths.meanings(persona.id) / f"{file_id}.md", body + "\n")
                memory.learn(file_id, meanings.Meaning(file_id, intention, body))
                catalog[intention] = file_id
                catalog_dirty = True
                logger.debug("brain.reflect created instruction", {"persona": persona, "file_id": file_id, "intention": intention})
            elif isinstance(delete, dict):
                target_intention = str(delete.get("intention", "")).strip()
                if not target_intention:
                    continue
                file_id = catalog.get(target_intention)
                if not file_id:
                    continue
                meaning_file = paths.meanings(persona.id) / f"{file_id}.md"
                if meaning_file.exists():
                    meaning_file.unlink()
                memory.unlearn(file_id)
                catalog = {k: v for k, v in catalog.items() if v != file_id}
                catalog_dirty = True
                logger.debug("brain.reflect deleted instruction", {"persona": persona, "file_id": file_id, "intention": target_intention})

        if catalog_dirty:
            paths.save_as_json(persona.id, paths.learned(persona.id), catalog)

    await consolidate(living)

    dispatch(Tock("reflect", {"persona": persona, "branch": "consolidated"}))
    return []
