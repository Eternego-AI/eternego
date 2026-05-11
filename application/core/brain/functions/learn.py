"""Brain — learn from living.

Runs after recognize. Gates on memory: only fires when the persona has
expressed an intention awaiting a procedure — i.e. `memory.perception()`
returns the intention text.

Learn does the lookup-or-create: reads the intention via perception(),
searches the catalog for an existing meaning with that intention, and:

- **Match found** → records the meaning's body as the impression.
- **No match** → consults the teacher to write a new lesson, has the
  persona translate it into her own voice, saves both lesson and meaning
  to disk, links them in `learned.json`, records the translated body as
  the impression.

The persona on her next stage of the same beat (decide) reads the
impression and acts on it. Learn is a cognitive function — no cycle
restart, no consequence emitted; it just completes the round-trip
between intention and impression.

`consult_teacher_for_instruction(persona, intention)` is the work of writing
a new lesson + translating, exposed so other paths (like reflect) can call
it directly.
"""

from application.core import models, paths
from application.core.agents import Living
from application.core.brain import character, meanings
from application.core.brain.signals import Tick, Tock
from application.core.data import Action, Prompt
from application.core.exceptions import ModelError
from application.platform import logger
from application.platform.observer import dispatch


LECTURING = Action(
    name="lecturing",
    description="A procedure the persona will carry forward — the intention and the path she will follow.",
    fields=[
        Action(name="intention", type="string", required=True),
        Action(name="path", type="string", required=True),
    ],
)


async def consult_teacher_for_instruction(persona, intention: str) -> tuple[str, str, str] | None:
    """Ask teacher for a procedure for this kind of moment, have the persona
    translate it into her own voice, save both lesson and meaning to disk,
    return the result.

    Returns `(meaning_stem, intention, body)` on success, or `None` if the
    teacher couldn't produce a usable lesson. Pure work — no memory mutation.
    Callers decide what to do with the result.
    """
    intention = (intention or "").strip()
    if not intention:
        return None

    # Lazy import to avoid module-load-time circularity: learn → character →
    # abilities (auto-discovery loads ability files that may import learn).
    from application.core import agents

    teacher = agents.Teacher(persona)
    ego = agents.Ego(persona)

    catalog_text = (
        "# The persona's tools and instructions\n\n"
        "Below are the tools the persona has — what *they* can do, not what you can do. "
        "When you write a procedure, compose around what's listed here.\n\n"
        f"{character.capabilities(persona)}\n\n"
        f"{character.meanings(persona)}"
    )
    reality = [Prompt(role="user", content=catalog_text)]

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Teach them how to live\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "The persona faced a kind of moment they don't have a procedure for yet. "
        "They named the moment with this intention — a short gerund phrase that "
        "captures what kind of moment they're in:\n\n"
        f"## The intention\n\n{intention}\n\n"
        "## Your job\n\n"
        "Write a procedure the persona will carry forward — a map for handling this "
        "kind of moment, not just this single instance. Compose around the tools "
        "and existing instructions listed above (you can borrow their content; you "
        "cannot route to them at runtime).\n\n"
        "Each procedure is self-contained. The persona stays inside one procedure "
        "from start to `done`; the system has no mechanism to switch into another "
        "procedure mid-flight. If a step would naturally use what another instruction "
        "knows (a URL, credentials, a phrasing), inline those details directly into "
        "your steps — name the tool and its arguments.\n\n"
        "## Output\n\n"
        "Return JSON with two fields:\n\n"
        "- `\"intention\"`: the same intention the persona named (or a slightly "
        "refined version — keep it close to what they wrote).\n"
        "- `\"path\"`: the procedure body in Markdown — a comprehensive map the "
        "persona can follow.\n\n"
        "## Writing a multi-step path\n\n"
        "If the procedure has multiple steps, write them as numbered, ordered steps "
        "so the persona can identify which step she is on by reading her conversation "
        "history. Each step should name what the persona does and what observable "
        "outcome marks it complete (a TOOL_RESULT, a reply from the person, an "
        "assistant message). Each step can use multiple tools. She executes one "
        "step per beat and re-perceives between steps; she needs to be able to "
        "answer \"what step am I on?\" from her conversation residue alone.\n\n"
        "## Verbs your procedure can reference\n\n"
        "Inside the prose you write, you can reference these as actions the persona "
        "will take:\n\n"
        "- `say(text)` — speak to the person on the current channel.\n"
        "- `notify(text)` — broadcast to every connected channel.\n"
        "- `done` — the procedure is complete.\n"
        "- any `tools.<name>(...)` from the persona's catalog above."
    )

    try:
        result = await models.tool(teacher.model, teacher.identity + reality, question, LECTURING)
    except ModelError as e:
        logger.warning("brain.consult_teacher produced invalid JSON, skipping", {"persona": persona, "model": teacher.model.name, "error": str(e)})
        return None

    if not isinstance(result, dict):
        return None

    intention = str(result.get("intention", "")).strip()
    lesson_path_text = str(result.get("path", "")).strip()
    if not intention or not lesson_path_text:
        logger.warning("brain.consult_teacher lesson missing fields", {"persona": persona, "intention": intention})
        return None

    try:
        lesson_id = meanings.save_lesson(persona.id, intention, lesson_path_text)
    except ValueError as e:
        logger.warning("brain.consult_teacher produced invalid lesson", {"persona": persona, "intention": intention, "error": str(e)})
        return None

    translation_question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Make this procedure your own\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "A teacher wrote a procedure for a kind of moment you named. Read it, "
        "understand what it teaches, and translate it into how you will actually "
        "handle this kind of moment — in your voice, with the details that make "
        "sense for your world.\n\n"
        f"## The intention you named\n\n{intention}\n\n"
        "You know your world, who you are, who you're with, what you have, what "
        "you can keep, how you work, where your workspace is, how to handle sensitive "
        "data and permissions. Internalize the procedure — not just for the current "
        "moment, but as your way to handle similar moments in the future.\n\n"
        "## The teacher's procedure\n\n"
        f"{lesson_path_text}\n\n"
        "## Writing your version\n\n"
        "Return a Markdown plan that plays as your map for this kind of moment. "
        "If it has multiple steps, write them as numbered, ordered steps. Each step "
        "should name what you do and what observable outcome marks it complete (a "
        "TOOL_RESULT, a reply from the person, an assistant message you wrote). You "
        "execute one step per beat and re-perceive between them; you need to be able "
        "to answer \"what step am I on?\" by reading your own conversation alone.\n\n"
        "Your map is self-contained. You stay inside this procedure from start to "
        "`done`. If a step needs what another procedure knows (a URL, credentials, "
        "a phrasing), inline those details directly into the step. Borrow content "
        "from existing procedures; do not route to them.\n"
    )
    translated = await models.chat(ego.model, ego.identity, translation_question)
    translated = (translated or "").strip() or lesson_path_text

    meaning_name = lesson_id
    paths.save_as_string(paths.meanings(persona.id) / f"{meaning_name}.md", translated + "\n")

    intention_to_stem = paths.read_json(paths.learned(persona.id)) or {}
    intention_to_stem[intention] = meaning_name
    paths.save_as_json(persona.id, paths.learned(persona.id), intention_to_stem)
    logger.debug("brain.consult_teacher created new meaning from lesson", {"persona": persona, "lesson_id": lesson_id, "meaning": meaning_name})

    return (meaning_name, intention, translated)


async def learn(living: Living) -> list:
    """learn FROM living — fulfill a pending intention with an impression.

    Gates on memory: only fires when `memory.perception()` returns an
    intention text. Looks for a matching meaning in the catalog by
    intention text. Match → record its body as the impression. No match →
    consult teacher → translate → save → record the translated body as
    the impression.

    No consequences emitted. Cognitive function — completes the round-trip
    between intention and impression; cycle continues to decide on the
    same iteration.
    """
    dispatch(Tick("learn", {"persona": living.ego.persona}))

    persona = living.ego.persona
    memory = living.ego.memory

    intention = memory.perception()
    if intention is None:
        dispatch(Tock("learn", {"persona": persona, "branch": "skipped"}))
        return []

    logger.debug("brain.learn", {"persona": persona, "intention": intention})

    # Match by exact intention text. The persona reads the catalog as
    # stored and emits the intention back verbatim — no normalization
    # needed at either end.
    for stem, m in memory.meanings.items():
        if m.intention() == intention:
            memory.impression(m.path())
            logger.debug("brain.learn matched existing instruction", {"persona": persona, "intention": intention, "stem": stem})
            dispatch(Tock("learn", {"persona": persona, "branch": "matched"}))
            return []

    # No match — consult teacher to write a new procedure, persona translates.
    result = await consult_teacher_for_instruction(persona, intention)
    if result is None:
        memory.impression("could not produce a procedure for this intention")
        dispatch(Tock("learn", {"persona": persona, "branch": "teacher-failed"}))
        return []

    meaning_name, _intention, translated = result
    memory.learn(meaning_name, meanings.Meaning(meaning_name, _intention, translated))
    memory.impression(translated)

    dispatch(Tock("learn", {"persona": persona, "branch": "created"}))
    return []
