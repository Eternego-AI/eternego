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

`consolidate(pulse, memory, ego)` is exposed so feed (importing past chat
data) can call it directly on a sandboxed past Living without reflect's
trigger gates.

Trigger for the night/idle work:
- If memory has nothing to consolidate, pass through.
- If phase is night, do the work immediately.
- Otherwise, await `pulse.is_idle()`. It sleeps the remaining-to-idle
  window; returns True if uninterrupted (idle confirmed → do the work),
  False if a nudge cancelled the wait (activity arrived → raise
  ReflectInterrupted).
"""

import json

from application.core import models, paths
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
    description="Step-by-step procedural refinements to existing instructions — what to do, in order — based on how the work actually unfolded today. Each update rewrites the instruction for one existing intention.",
    fields=[
        Action(
            name="updates",
            type="array",
            required=True,
            items=Action(
                fields=[
                    Action(name="intention", type="string", required=True),
                    Action(name="instruction", type="string", required=True),
                ],
            ),
        ),
    ],
)


async def consolidate(pulse, memory, ego) -> bool:
    """Distill the conversation in `memory` into context + person files,
    then archive messages and forget. No trigger checks, no Tick/Tock
    dispatch — pure work.

    Returns True if consolidation happened, False if there was nothing to do
    or the model failed."""
    persona = ego.persona

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
        "# ▶ YOUR TASK: What do you want to keep as your memory?\n"
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
        result = await models.tool(ego.model, ego.identity + memory.context_prompt + pulse.hint(), question, CONSOLIDATING)
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


async def reflect(pulse, memory, ego) -> list:
    """reflect ON living — look back upon what was."""
    dispatch(Tick("reflect", {"persona": ego.persona}))

    persona = ego.persona
    logger.debug("brain.reflect", {"persona": persona, "messages_count": len(memory.messages)})

    if not memory.messages:
        dispatch(Tock("reflect", {"persona": persona, "branch": "no-messages"}))
        return []

    # Morning is for waking and starting, not for reflection. Reflect runs
    # during NIGHT (consolidating the day) or when the persona is idle
    # during DAY (a natural pause). Never during MORNING.
    if pulse.phase == Phase.MORNING:
        dispatch(Tock("reflect", {"persona": persona, "branch": "morning-skip"}))
        return []

    if pulse.phase != Phase.NIGHT:
        if not await pulse.is_idle():
            dispatch(Tock("reflect", {"persona": persona, "branch": "not-idle"}))
            raise ReflectInterrupted()

    # Procedural memory consolidation: ask the persona to look at the
    # instructions she used today and refine the bodies of the ones whose
    # use revealed something worth keeping. Reflection does not create new
    # meanings (creation lives in learn, deliberately, through teacher or
    # her own thinking) and does not delete them (deletion lives in
    # troubleshooting, where the user is in the loop). Refine only.

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Refine the instructions you used today\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "This is reflection, not action. No tools run from your response — "
        "only the JSON described below has effect. Walk through what already "
        "happened.\n\n"
        "Your active memory will not survive forever. What survives are your "
        "instructions: the ones you read every time the same kind of moment "
        "comes round. Tonight you refine those instructions based on how "
        "today went.\n\n"
        "The goal is concrete. Future-you should fail less, hesitate less, and "
        "move faster than current-you on the same kinds of work. Every error "
        "you hit, every workflow you figured out, every step that turned out "
        "to matter — these belong in the instructions you already have for "
        "those moments.\n\n"
        "Instructions hold experience, not decisions. The lived shape of the "
        "work in steps — the order, the gotchas, the argument names, the "
        "recovery on failure. Decisions and principles belong in your traits "
        "and context, not here.\n\n"
        "## What to look for\n\n"
        "Walk through the whole conversation. For each instruction you loaded "
        "today (look for your `load_instruction` calls and the TOOL_RESULTs "
        "that followed), ask:\n\n"
        "- What did the work require that the instruction didn't say?\n"
        "- What failed because the instruction was wrong or incomplete?\n"
        "- What worked on a second try that the instruction could capture for next time?\n"
        "- What would future-you need to know to do this without anyone "
        "walking her through it again?\n\n"
        "Bias toward operational specifics. Concrete details that future-you "
        "can follow beat themes she has to interpret.\n\n"
        "## What to return\n\n"
        "Return a JSON object with an `updates` list. Each update rewrites the "
        "instruction for one existing intention:\n\n"
        "- `{\"intention\": \"<existing intention>\", \"instruction\": \"<full new instruction>\"}` — "
        "the `instruction` REPLACES the existing one in full. The `intention` "
        "must match a custom instruction you already have; built-in "
        "instructions are immutable.\n\n"
        "Reflection does not create or delete instructions. If you encountered "
        "a kind of moment you don't have an instruction for, do nothing here — "
        "next time you meet that moment you will recognise it and learn it "
        "then. If an instruction is broken beyond refinement, leave it; "
        "deletion belongs to troubleshooting, with the person in the loop.\n\n"
        "Return `{\"updates\": []}` only if there's no operational lesson "
        "worth carrying back into the instructions you used today."
    )

    try:
        response = await models.tool(
            ego.model,
            ego.identity + memory.context_prompt + pulse.hint(),
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

        # Each item is a flat {intention, instruction} update. Reflection only
        # refines existing instructions; creation lives in learn, deletion in
        # troubleshooting. Items targeting unknown intentions are ignored
        # (catalog keeps only what the persona already had).
        for item in updates:
            if not isinstance(item, dict):
                continue
            target_intention = str(item.get("intention", "")).strip()
            body = str(item.get("instruction", "")).strip()
            if not target_intention or not body:
                continue
            file_id = catalog.get(target_intention)
            if not file_id:
                logger.debug("brain.reflect update no match", {"persona": persona, "intention": target_intention})
                continue
            paths.save_as_string(paths.meanings(persona.id) / f"{file_id}.md", body + "\n")
            memory.learn(file_id, meanings.Meaning(file_id, target_intention, body))
            logger.debug("brain.reflect refined instruction", {"persona": persona, "file_id": file_id, "intention": target_intention})

    await consolidate(pulse, memory, ego)

    dispatch(Tock("reflect", {"persona": persona, "branch": "consolidated"}))
    return []
