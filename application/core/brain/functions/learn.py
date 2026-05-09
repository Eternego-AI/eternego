"""Brain — learn from living.

Runs after recognize. If recognize chose an existing meaning (memory.meaning is set),
learn passes through. If recognize produced an impression but no existing
meaning matched (memory.meaning is None), learn consults the teacher.

The teacher's only output is a lesson — an intention and a path. No routing
to existing meanings, no direct tool/ability dispatch, no speaking through
the persona's voice. The teacher sees less than recognize (no conversation
history, no TOOL_RESULTs); routing or speaking from that position would be
fabricating context. Writing a procedure is what the teacher can honestly
do with an impression and the persona's capability catalog.

Once the teacher writes the lesson, the persona's thinking model translates
it into a meaning in her own voice. The translated meaning is saved next to
the lesson, linked in `learned.json`, and set as memory.meaning so decide
takes over on the same beat.

If the teacher cannot produce a usable response, learn passes through
silently — no message is injected into living.ego.memory. The next
recognize will read the same moment and decide again.
"""

from application.core import models, paths
from application.core.agents import Living
from application.core.brain import character, meanings
from application.core.brain.signals import Tick, Tock
from application.core.data import Prompt
from application.core.exceptions import ModelError
from application.platform import logger
from application.platform.observer import dispatch


async def learn(living: Living) -> list:
    """learn FROM living — draw the lesson the moment exposed."""
    dispatch(Tick("learn", {"persona": living.ego.persona}))

    persona = living.ego.persona
    memory = living.ego.memory
    teacher = living.teacher

    if memory.meaning is not None:
        dispatch(Tock("learn", {"persona": persona}))
        return []

    impression = (memory.impression or "").strip()
    if not impression:
        logger.debug("brain.learn skipping — no impression", {"persona": persona})
        dispatch(Tock("learn", {"persona": persona}))
        return []

    logger.debug("brain.learn", {"persona": persona, "impression": impression})

    catalog_text = (
        "# The persona's capabilities and meanings\n\n"
        "Below are the tools, abilities, what *they* can do, not what you can do. "
        "When you write a lesson, compose around what's listed here.\n\n"
        f"{character.capabilities(persona)}\n\n"
        "Below are meanings the persona experienced, so they know how to handle similar situations, they get an impression that matches with an intention that gives them a meaning to follow.\n\n"
        f"{character.meanings(persona)}"
    )
    reality = [Prompt(role="user", content=catalog_text)]

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Teach them how to live\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "The persona faced a situation they cannot handle with the meanings they already have. "
        "They produced an impression of the moment.\n\n"
        f"## The impression\n\n{impression}\n\n"
        "## What a meaning is\n\n"
        "A meaning is the persona's name for a kind of moment — what they recognize when an "
        "impression arrives. The lesson you write becomes that meaning's procedure: when the "
        "persona next reads a moment of this kind, they enter this meaning and follow your "
        "procedure from start to `done`.\n\n"
        "A meaning is self-contained. The persona stays inside one meaning from start to `done`; "
        "the system has no mechanism to switch into or enter another meaning mid-procedure. If a "
        "step in your procedure would naturally use what another meaning knows (e.g., the OAuth "
        "credentials for posting to X), inline those details directly into your steps — name the "
        "tool and its arguments. Do not write instructions like \"switch to meanings.X\" or "
        "\"enter meanings.Y\"; the persona cannot execute that.\n\n"
        "Write a lesson the persona will carry forward — a procedure for handling this kind of "
        "moment, not just this single instance. Compose around the persona's existing tools, "
        "abilities, and the knowledge already encoded in the meanings listed above (you can "
        "borrow their content; you cannot route to them at runtime).\n\n"
        "## Output\n\n"
        "Return JSON with two fields:\n\n"
        "- `\"intention\"`: a short gerund phrase naming the kind of moment "
        "(e.g. words ending in -ing — what the persona is doing).\n"
        "- `\"path\"`: the lesson body in Markdown — a comprehensive map the persona can follow "
        "to handle this kind of moment, now and in similar moments later.\n\n"
        "## Writing a multi-step path\n\n"
        "If the procedure has multiple steps, write them as numbered, ordered steps so the persona "
        "can identify which step she is on by reading her own conversation history. Each step "
        "should name what the persona does and what observable outcome marks it complete (a "
        "TOOL_RESULT, a reply from the person, an assistant message), each step can use multiple tools and abilities. "
        "The persona's decide stage will execute one step per beat and re-perceive between steps; she needs to be able to "
        "answer \"what step am I on?\" from her conversation residue alone.\n\n"
        "## Verbs your lesson body can reference\n\n"
        "When the persona enters this meaning, the lesson's `path` is read by their decide stage. "
        "Inside the prose you write, you can reference these verbs as actions the persona will take "
        "during the procedure:\n\n"
        "- `say(text)` — the persona speaks to the person on the current channel.\n"
        "- `notify(text)` — the persona broadcasts to every connected channel.\n"
        "- `done` — the procedure is complete; the cycle ends.\n\n"
        "Other specials exist for self-care (memory, meaning catalog, stopping). Lessons compose "
        "around `say`, `notify`, and `done`; the others belong to the persona's own judgment, not "
        "to the lessons you write."
    )

    try:
        result = await models.chat_json(teacher.model, teacher.identity + reality, question)
    except ModelError as e:
        logger.warning("brain.learn produced invalid JSON, skipping", {"persona": persona, "model": teacher.model.name, "error": str(e)})
        dispatch(Tock("learn", {"persona": persona}))
        return []

    if not isinstance(result, dict):
        dispatch(Tock("learn", {"persona": persona}))
        return []

    intention = str(result.get("intention", "")).strip()
    lesson_path_text = str(result.get("path", "")).strip()
    if not intention or not lesson_path_text:
        logger.warning("brain.learn lesson missing fields", {"persona": persona, "intention": intention})
        dispatch(Tock("learn", {"persona": persona}))
        return []

    try:
        lesson_id = meanings.save_lesson(persona.id, intention, lesson_path_text)
    except ValueError as e:
        logger.warning("brain.learn produced invalid lesson", {"persona": persona, "intention": intention, "error": str(e)})
        dispatch(Tock("learn", {"persona": persona}))
        return []

    translation_question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Learn the lesson\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "You got an impression from a situation you faced, and a teacher gave you a lesson to learn from it. "
        "The lesson is below. Read it carefully, understand the principle it teaches, and translate it into "
        "how you will actually handle the situation.\n\n"
        f"## The impression\n\n{impression}\n\n"
        "You know your world, who you are, who you are with, what you have, what you can keep, what remains "
        "with you, how you work, where your workspace is, how to handle sensitive data and permissions. "
        "Internalize the lesson — not just for the current impression, but as your way to handle similar "
        "situations in the future.\n\n"
        "## The lesson\n\n"
        f"{lesson_path_text}\n\n"
        "## Writing your map\n\n"
        "Return a Markdown plan that plays as your map for this kind of moment, now and later. "
        "If the procedure has multiple steps, write them as numbered, ordered steps. Each step should "
        "name what you do and what observable outcome marks it complete (a TOOL_RESULT, a reply from "
        "the person, an assistant message you wrote). Your decide stage will execute one step per "
        "beat and re-perceive between them; you need to be able to answer \"what step am I on?\" by "
        "reading your own conversation history alone.\n\n"
        "Your map is self-contained. You stay inside this meaning from start to `done`; there is "
        "no way to switch into or enter another meaning mid-procedure. If a step would naturally "
        "use what another meaning knows (a URL, credentials, a phrasing), inline those details "
        "directly into the step — name the tool and its arguments. Do not write \"switch to meanings.X\" "
        "or \"enter meanings.Y\"; you cannot execute that. Borrow content from existing meanings; "
        "do not route to them.\n\n"
    )
    translated = await models.chat(living.ego.model, living.ego.identity, translation_question)
    translated = (translated or "").strip() or lesson_path_text

    meaning_name = lesson_id
    paths.save_as_string(paths.meanings(persona.id) / f"{meaning_name}.md", translated + "\n")

    memory.learn(meaning_name, meanings.Meaning(meaning_name, intention, translated))
    memory.meaning = meaning_name

    intention_to_stem = paths.read_json(paths.learned(persona.id)) or {}
    intention_to_stem[intention] = meaning_name
    paths.save_as_json(persona.id, paths.learned(persona.id), intention_to_stem)
    logger.debug("brain.learn created new meaning from lesson", {"persona": persona, "lesson_id": lesson_id, "meaning": meaning_name})

    dispatch(Tock("learn", {"persona": persona}))
    return []
