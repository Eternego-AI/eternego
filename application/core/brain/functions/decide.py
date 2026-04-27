"""Brain — decide for living.

One cognitive call per tick when recognize handed us a meaning. Decide reads
the meaning's prompt and emits a single-key JSON object in the unified shape.

Extends recognize's vocabulary with:
- `{"notify": "text"}` — broadcast (agent fans out)
- `{"clear_memory": null}` — wipe active messages
- `{"remove_meaning": {name}}` — delete a custom meaning
- `{"stop": null}` — stop until the person returns

These specials, plus `say`, `done`, and prose, are handled inline. Tools and
abilities are returned as a capability list for clock's executor to run.

If the model returns prose alongside a JSON action, the prose is dispatched
as a say (the persona's voice) and the action still runs. If the model
returns prose with no JSON, the prose is dispatched as say and decide
returns an empty list.
"""

from application.core import models, paths
from application.core.agents import Living
from application.core.brain import situation
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
        "Memory and self-care:\n"
        "- `{\"clear_memory\": null}` — wipe the current messages.\n"
        "- `{\"remove_meaning\": {\"name\": \"<name>\"}}` — delete a custom meaning.\n"
        "- `{\"stop\": null}` — stop yourself until someone speaks.\n\n"
        "Tools and abilities:\n"
        "- `{\"tools.<name>\": { ...args }}` — run a platform tool.\n"
        "- `{\"abilities.<name>\": { ...args }}` — run an ability.\n\n"
        "Done:\n"
        "- `{\"done\": null}` — this cycle is finished.\n\n"
        "Any prose outside the JSON will be sent to the person as a `say`."
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
            meaning_file = paths.meanings(persona.id) / f"{name}.py"
            if meaning_file.exists():
                meaning_file.unlink()
                memory.unlearn(name)
                result_text = f"removed meaning: {name}"
            else:
                status, result_text = "error", f"meaning not found: {name}"
        memory.add_tool_result("remove_meaning", value, status, result_text)

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
