"""Brain — learn from living.

Runs after recognize. If recognize chose a meaning (memory.ability != 0),
learn passes through — nothing to acquire in this moment. If recognize
produced an impression but no existing meaning matched (memory.ability == 0),
learn consults a teacher — either naming an existing meaning that fits
(recognize simply missed it) or writing a new one the persona will carry
forward.

Learn uses living.teacher's identity, not the persona's. Teacher is not the
persona; it is the architect who builds the persona's meanings.

Learn requires living.teacher.model (the frontier). If absent or the
teacher cannot produce a usable response, learn passes through silently —
no message is injected into living.ego.memory. The next recognize will read
the same moment and decide again.
"""

from application.core import models
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

    if not teacher.model:
        logger.debug("brain.learn skipping — no frontier", {"persona": persona})
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

    # New meaning — save the module and set state.
    elif selector == "new_meaning":
        spec = value if isinstance(value, dict) else {}
        name = str(spec.get("name", "")).strip()
        code_lines = spec.get("code_lines")
        if isinstance(code_lines, list) and code_lines:
            code = "\n".join(str(line) for line in code_lines)
        else:
            code = ""
        if name and code:
            try:
                meaning_name = meanings.save_meaning(persona.id, name, code)
                learned = meanings.load(persona, meaning_name)
                if learned is not None:
                    memory.learn(meaning_name, learned)
                memory.meaning = meaning_name
                meaning_names = list(memory.meanings.keys())
                memory.ability = meaning_names.index(meaning_name) + 1
                logger.debug("brain.learn created new meaning", {"persona": persona, "meaning": meaning_name})
            except (SyntaxError, ValueError) as e:
                logger.warning("brain.learn produced invalid code", {"persona": persona, "name": name, "error": str(e)})

    # Tool / Ability — declare as a consequence; clock's executor runs it.
    elif selector.startswith("tools.") or selector.startswith("abilities."):
        args = value if isinstance(value, dict) else {}
        consequences.append({selector: args})
        logger.debug("brain.learn dispatched capability", {"persona": persona, "selector": selector, "args": args})

    else:
        logger.warning("brain.learn unknown selector", {"persona": persona, "selector": selector})

    dispatch(Tock("learn", {"persona": persona}))
    return consequences
