"""Brain — decide for living.

One cognitive call per tick when recognize handed us a meaning. Decide reads
the meaning's prompt and emits a single-key JSON object in the unified shape.

Extends recognize's vocabulary with:
- `{"notify": "text"}` — broadcast (agent fans out)
- `{"clear_memory": null}` — wipe active messages
- `{"remove_meaning": {name}}` — delete a custom meaning
- `{"revise_meaning": "<new path>"}` — replace the current custom meaning's path
- `{"stop": null}` — stop until the person returns

These specials, plus `say`, `done`, and prose, are handled inline. Tools and
abilities are returned as a capability list for clock's executor to run.

`revise_meaning` carries the full new path text directly — the persona writes
the wisdom at the same moment she chooses to capture it, no second model call.
It's offered only when the current meaning is custom; built-ins are stable
system vocabulary, not revisable. The persona can still `remove_meaning` and
re-learn if she wants a custom replacement.

If the model returns prose alongside a JSON action, the prose is dispatched
as a say (the persona's voice) and the action still runs. If the model
returns prose with no JSON, the prose is dispatched as say and decide
returns an empty list.
"""

from application.core import models, paths
from application.core.agents import Living
from application.core.brain import meanings, situation
from application.core.brain.signals import Tick, Tock
from application.core.data import Message, Prompt
from application.core.exceptions import ModelError
from application.platform import logger
from application.platform.observer import Command, dispatch


async def decide(living: Living) -> list:
    """decide FOR living — choose the next action on its behalf."""
    dispatch(Tick("decide", {"persona": living.ego.persona}))

    persona = living.ego.persona
    memory = living.ego.memory

    meaning = memory.meanings.get(memory.meaning)
    if not meaning:
        dispatch(Tock("decide", {"persona": persona}))
        return []

    is_custom = memory.meaning in memory.custom_meanings
    self_care_lines = [
        "Memory and self-care:",
        "- `{\"clear_memory\": null}` — wipe the current messages.",
        "- `{\"remove_meaning\": {\"name\": \"<name>\"}}` — delete a custom meaning.",
    ]
    if is_custom:
        self_care_lines.append(
            "- `{\"revise_meaning\": \"<full new path text>\"}` — when something you just "
            "did or learned should be how you handle this situation next time, write the "
            "complete new path here. Whatever you write replaces the current path. "
            "Use sparingly — only when the meaning is genuinely wrong, missing, or could "
            "capture something useful for next time. Plain prose, paragraphs separated by "
            "`\\n\\n`. No headings, no code blocks."
        )
    self_care_lines.append("- `{\"stop\": null}` — stop yourself until someone speaks.")
    self_care_block = "\n".join(self_care_lines)

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"# ▶ YOUR TASK: {memory.meaning.capitalize()}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{situation.time()}\n\n"
        f"{meaning.path()}\n\n"
        "## Output\n\n"
        "Return a single-key JSON object. The key names the action; the value carries what it needs. "
        "Your tools and abilities are in your identity above — pick one by its full selector.\n\n"
        "Voice:\n"
        "- `{\"say\": \"<text>\"}` — speak to the person on the current channel.\n"
        "- `{\"notify\": \"<text>\"}` — broadcast to every connected channel.\n\n"
        f"{self_care_block}\n\n"
        "Tools and abilities:\n"
        "- `{\"tools.<name>\": { ...args }}` — run a platform tool.\n"
        "- `{\"abilities.<name>\": { ...args }}` — run an ability.\n\n"
        "Done:\n"
        "- `{\"done\": null}` — this cycle is finished.\n\n"
        "Prefer `say` for speaking. Prose around the JSON is also sent to the person — "
        "using both means the same message reaches them twice."
    )

    try:
        prose, result = await models.chat_action(living.ego.model, living.ego.identity + living.pulse.hint() + memory.prompts, question)
    except ModelError as e:
        logger.debug("brain.decide chose prose, dispatching as say", {"persona": persona, "meaning": memory.meaning, "raw": e.raw})
        dispatch(Command("Persona wants to say", {"persona": persona, "text": e.raw}))
        memory.meaning = None
        memory.ability = 0
        dispatch(Tock("decide", {"persona": persona}))
        return []

    if not isinstance(result, dict) or not result:
        memory.meaning = None
        memory.ability = 0
        dispatch(Tock("decide", {"persona": persona}))
        return []

    # Prose around the JSON action is the persona's voice. Words after words
    # is the action itself; if the model wrote prose alongside its selector,
    # those words go to the person. The selector then runs as its own action.
    if prose:
        dispatch(Command("Persona wants to say", {"persona": persona, "text": prose}))
        logger.debug("brain.decide dispatched prose as say", {"persona": persona, "prose_length": len(prose)})

    if len(result) > 1:
        logger.warning("brain.decide returned multiple keys; using first", {"persona": persona, "keys": list(result.keys())})
    selector, value = next(iter(result.items()))
    selector = str(selector).strip()

    consequences: list = []

    if selector == "done":
        pass

    elif selector == "say":
        text = str(value) if value else ""
        if text:
            dispatch(Command("Persona wants to say", {"persona": persona, "text": text}))

    elif selector == "notify":
        text = str(value) if value else ""
        if text:
            memory.remember(Message(content=text, prompt=Prompt(role="assistant", content=text)))
            dispatch(Command("Persona wants to notify", {"persona": persona, "text": text}))

    elif selector == "clear_memory":
        memory.forget()
        memory.add_tool_result("clear_memory", value, "ok", "memory cleared")

    elif selector == "remove_meaning":
        args = value if isinstance(value, dict) else {}
        name = args.get("name", "")
        status = "ok"
        result_text = ""
        if not name:
            status, result_text = "error", "name is required"
        else:
            meaning_file = paths.meanings(persona.id) / f"{name}.md"
            if meaning_file.exists():
                meaning_file.unlink()
                memory.unlearn(name)
                paths.save_as_json(persona.id, paths.learned(persona.id), {n: n for n in memory.custom_meanings})
                result_text = f"removed meaning: {name}"
            else:
                status, result_text = "error", f"meaning not found: {name}"
        memory.add_tool_result("remove_meaning", value, status, result_text)

    elif selector == "revise_meaning":
        status = "ok"
        result_text = ""
        meaning_name = memory.meaning
        new_path = (str(value).strip() if value is not None else "")
        if not is_custom or meaning_name is None:
            status, result_text = "error", "only custom meanings can be revised"
        elif not new_path:
            status, result_text = "error", "revise_meaning needs the new path text"
        else:
            current = memory.custom_meanings.get(meaning_name)
            if current is None:
                status, result_text = "error", "current meaning could not be loaded"
            else:
                body = f"# {current.intention()}\n\n{new_path}\n"
                paths.save_as_string(paths.meanings(persona.id) / f"{meaning_name}.md", body)
                memory.learn(meaning_name, meanings.Meaning(meaning_name, current.intention(), new_path))
                result_text = f"revised meaning: {meaning_name}"
        memory.add_tool_result("revise_meaning", value, status, result_text)

    elif selector == "stop":
        dispatch(Command("Persona requested stop", {"persona": persona}))

    elif "." in selector:
        namespace, _name = selector.split(".", 1)
        if namespace == "tools" or namespace == "abilities":
            args = value if isinstance(value, dict) else {}
            consequences.append({selector: args})
        else:
            logger.warning("brain.decide unknown namespace", {"persona": persona, "namespace": namespace, "selector": selector})

    else:
        logger.warning("brain.decide unknown selector", {"persona": persona, "selector": selector})

    memory.meaning = None
    memory.ability = 0
    dispatch(Tock("decide", {"persona": persona}))
    return consequences
