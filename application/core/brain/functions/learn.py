"""Brain — learn from living.

Runs after recognize. If recognize chose a meaning (memory.ability != 0),
learn passes through — nothing to acquire in this moment. If recognize
produced an impression but no existing meaning matched (memory.ability == 0),
learn consults a teacher.

Teacher's response is one of four shapes:

- a tool or ability call — declared as a consequence; clock's executor runs it.
- an existing meaning pointer — recognize simply missed it; learn sets state.
- a lesson — the frontier wrote a first draft. Learn writes it to the
  persona's lessons directory, asks the persona's thinking model to translate
  it into a meaning in her own voice, writes the meaning, and links the two
  in `learned.json`.

Learn uses living.teacher's identity for the lesson decision and the
persona's own Ego for the translation. Teacher's model is the persona's
frontier when configured, otherwise her thinking model — the persona tries
her best with what she has rather than skipping moments she doesn't know
how to handle.

If the teacher cannot produce a usable response, learn passes through
silently — no message is injected into living.ego.memory. The next
recognize will read the same moment and decide again.
"""

from application.core import models, paths
from application.core.agents import Living
from application.core.brain import meanings
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

    if memory.ability != 0:
        dispatch(Tock("learn", {"persona": persona}))
        return []

    impression = (memory.impression or "").strip()
    if not impression:
        # Recognize concluded the turn cleanly (say or done) — nothing to escalate.
        logger.debug("brain.learn skipping — no impression", {"persona": persona})
        dispatch(Tock("learn", {"persona": persona}))
        return []

    logger.debug("brain.learn", {"persona": persona, "impression": impression})

    meaning_map = memory.meanings
    custom_lines = [
        f"- **{name}**: {m.intention()}"
        for name, m in memory.custom_meanings.items()
    ]
    custom_text = "\n".join(custom_lines) or "(none yet)"
    reality = [Prompt(
        role="user",
        content=f"# Custom meanings the persona already has\n\n{custom_text}",
    )]

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Handle this moment\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "The persona formed the impression below. That impression is your only ground; "
        "the conversation itself stays with the persona. Do not ask for it.\n\n"
        f"## The impression\n\n{impression}\n\n"
        "Look at what the persona already has — tools, abilities, built-in meanings (in "
        "your knowledge), and custom meanings (above). If one of them handles this "
        "situation, return its selector as described in your output rules. If nothing "
        "fits, design a new meaning following the rules in your knowledge.\n\n"
        "Prefer existing capabilities when one fits — they are already proven. Design a "
        "new meaning only when the moment truly needs something new. Generic meanings "
        "serve more situations and save on future escalations, but when the task is tied "
        "to this person's habits or routine, be specific."
    )

    try:
        result = await models.chat_json(teacher.model, teacher.identity + reality, question)
    except ModelError as e:
        logger.warning("brain.learn produced invalid JSON, skipping", {"persona": persona, "model": teacher.model.name, "error": str(e)})
        dispatch(Tock("learn", {"persona": persona}))
        return []

    if not isinstance(result, dict) or not result:
        dispatch(Tock("learn", {"persona": persona}))
        return []

    if len(result) > 1:
        logger.warning("brain.learn returned multiple keys; using first", {"persona": persona, "keys": list(result.keys())})
    selector, value = next(iter(result.items()))
    selector = str(selector).strip()

    consequences: list = []

    # Existing meaning — set state, let decide take over.
    if selector.startswith("meanings."):
        name = selector.split(".", 1)[1]
        if name in meaning_map:
            impression_value = str(value) if value else impression
            memory.impression = impression_value
            memory.meaning = name
            meaning_names = list(memory.meanings.keys())
            memory.ability = meaning_names.index(name) + 1
            logger.debug("brain.learn matched existing meaning", {"persona": persona, "meaning": name})
        else:
            logger.warning("brain.learn named nonexistent meaning", {"persona": persona, "name": name})

    # New lesson — frontier wrote a first draft. Save it, ask the persona to
    # translate into her own meaning, link them in learned.json.
    elif selector == "lesson":
        spec = value if isinstance(value, dict) else {}
        intention = str(spec.get("intention", "")).strip()
        lesson_path_text = str(spec.get("path", "")).strip()
        if not intention or not lesson_path_text:
            logger.warning("brain.learn lesson missing fields", {"persona": persona, "intention": intention})
        else:
            try:
                lesson_id = meanings.save_lesson(persona.id, intention, lesson_path_text)
            except ValueError as e:
                logger.warning("brain.learn produced invalid lesson", {"persona": persona, "intention": intention, "error": str(e)})
                lesson_id = None

            if lesson_id is not None:
                translation_question = (
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "# ▶ YOUR TASK: Learn the lesson\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Your teacher just taught you a lesson about the kind of moment you are "
                    "in. Learn it. Find your own path through this moment — what to do, what "
                    "to use, what to watch for, what to say — then write the prompt future-you "
                    "will read the next time this kind of moment comes up.\n\n"
                    "## The lesson\n\n"
                    f"{lesson_path_text}\n\n"
                    "The lesson is the principle. Your prompt is how the principle works "
                    "through you — your tools, your abilities, your credentials, your notes, "
                    "the way you already do things, the person you live with. Where the lesson "
                    "names an input, name how you will get it. Where it names a mechanism, "
                    "name the specific move you will make. Where it names an outcome, name how "
                    "you will recognize it and what you will say when you reach it.\n\n"
                    "If something the lesson assumes is not yet available — credentials you do "
                    "not have, files you have not made, an account not yet linked — write that "
                    "into the prompt explicitly, so future-you knows to ask, find, or work "
                    "around it before acting.\n\n"
                    "Address yourself in second person, plain prose, paragraphs separated by "
                    "`\\n\\n`. No headings, no code blocks, no JSON — return only the prompt "
                    "text."
                )
                translated = await models.chat(living.ego.model, living.ego.identity, translation_question)
                translated = (translated or "").strip() or lesson_path_text

                meaning_name = lesson_id
                body = f"# {intention}\n\n{translated}\n"
                paths.save_as_string(paths.meanings(persona.id) / f"{meaning_name}.md", body)

                memory.learn(meaning_name, meanings.Meaning(meaning_name, intention, translated))
                memory.meaning = meaning_name
                meaning_names = list(memory.meanings.keys())
                memory.ability = meaning_names.index(meaning_name) + 1

                paths.save_as_json(persona.id, paths.learned(persona.id), {n: n for n in memory.custom_meanings})
                logger.debug("brain.learn created new meaning from lesson", {"persona": persona, "lesson_id": lesson_id, "meaning": meaning_name})

    # Tool / Ability — declare as a consequence; clock's executor runs it.
    elif selector.startswith("tools.") or selector.startswith("abilities."):
        args = value if isinstance(value, dict) else {}
        consequences.append({selector: args})
        logger.debug("brain.learn dispatched capability", {"persona": persona, "selector": selector, "args": args})

    else:
        logger.warning("brain.learn unknown selector", {"persona": persona, "selector": selector})

    dispatch(Tock("learn", {"persona": persona}))
    return consequences
