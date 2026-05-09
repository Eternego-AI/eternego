"""Brain — decide for living.

One cognitive call per tick when recognize handed us a meaning. Decide reads
the meaning's prompt and emits JSON describing what to do next.

Single action shape:
- `{"say": "<text>"}`, `{"notify": "<text>"}`
- `{"clear_memory": null}`, `{"remove_meaning": {name}}`, `{"stop": null}`
- `{"tools.<name>": { ...args }}`, `{"abilities.<name>": { ...args }}`
- `{"done": null}`

Multi-step shape:
- `{"steps": [<single-action>, <single-action>, ...]}` — a list of the same
  single-action objects above. Items run in order; voice and specials run
  inline, tools and abilities are queued as consequences for clock's
  executor. On the first non-ok status from a tool/ability, clock skips
  the rest and the cycle restarts.

Meaning refinement is not decide's job — reflect handles it after decide
finishes. Decide focuses on action; reflect on what to keep.

If the model returns prose alongside JSON, the prose is dispatched as a say
(fallback for models that don't emit clean JSON). Meaning state
(memory.meaning) is left set on exit — reflect reads it for refinement, then
clears it.
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

    self_care_block = (
        "Memory and self-care:\n"
        "- `{\"clear_memory\": null}` — wipe the current messages.\n"
        "- `{\"remove_meaning\": {\"name\": \"<name>\"}}` — delete a custom meaning.\n"
        "- `{\"stop\": null}` — stop yourself until someone speaks."
    )

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"# ▶ YOUR TASK: {memory.impression}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{situation.time()}\n\n"
        f"{meaning.path()}\n\n"
        "## Output\n\n"
        "Return a single-key JSON object naming the action, or wrap several "
        "in `{\"steps\": [...]}` to chain them in one beat. Each step is one "
        "of the single-key shapes below. Your tools and abilities are in your "
        "identity above — pick one by its full selector.\n\n"
        "If you see multiple steps are there in the procedure, pay attention to the conversation to see on which step you are and continue from there.\n\n"
        "Voice:\n"
        "- `{\"say\": \"<text>\"}` — speak to the person on the current channel.\n"
        "- `{\"notify\": \"<text>\"}` — broadcast to every connected channel.\n\n"
        f"{self_care_block}\n\n"
        "Tools and abilities:\n"
        "- `{\"tools.<name>\": { ...args }}` — run a platform tool.\n"
        "- `{\"abilities.<name>\": { ...args }}` — run an ability.\n\n"
        "Done:\n"
        "- `{\"done\": null}` — this cycle is finished.\n\n"
        "When you use `steps`, items run in order; voice and self-care run "
        "inline, tools and abilities run after this beat. On the first "
        "non-ok status the rest are skipped and the cycle restarts so you "
        "re-perceive.\n\n"
        "Prefer `say` for speaking. Prose around the JSON is also sent to the person — "
        "using both means the same message reaches them twice."
    )

    try:
        prose, result = await models.chat_action(living.ego.model, living.ego.identity + living.pulse.hint() + memory.prompts, question)
    except ModelError as e:
        logger.debug("brain.decide chose prose, dispatching as say", {"persona": persona, "meaning": memory.meaning, "raw": e.raw})
        dispatch(Command("Persona wants to say", {"persona": persona, "text": e.raw}))
        memory.meaning = None
        dispatch(Tock("decide", {"persona": persona}))
        return []

    if not isinstance(result, dict) or not result:
        memory.meaning = None
        dispatch(Tock("decide", {"persona": persona}))
        return []

    # Prose around the JSON action is the persona's voice. Words after words
    # is the action itself; if the model wrote prose alongside its selector,
    # those words go to the person. The selector then runs as its own action.
    if prose:
        dispatch(Command("Persona wants to say", {"persona": persona, "text": prose}))
        logger.debug("brain.decide dispatched prose as say", {"persona": persona, "prose_length": len(prose)})

    steps_value = result.get("steps")
    items = steps_value if isinstance(steps_value, list) else [result]

    consequences: list = []

    for item in items:
        if not isinstance(item, dict) or not item:
            continue
        if len(item) > 1:
            logger.warning("brain.decide step has multiple keys; using first", {"persona": persona, "keys": list(item.keys())})
        selector, value = next(iter(item.items()))
        selector = str(selector).strip()

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
            name = args.get("name", "").removeprefix("meanings.")
            status = "ok"
            result_text = ""
            if not name:
                status, result_text = "error", "name is required"
            else:
                meaning_file = paths.meanings(persona.id) / f"{name}.md"
                if meaning_file.exists():
                    meaning_file.unlink()
                    memory.unlearn(name)
                    # Drop every map entry pointing at this stem (defensive — usually one).
                    intention_to_stem = paths.read_json(paths.learned(persona.id)) or {}
                    intention_to_stem = {i: s for i, s in intention_to_stem.items() if s != name}
                    paths.save_as_json(persona.id, paths.learned(persona.id), intention_to_stem)
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

    dispatch(Tock("decide", {"persona": persona}))
    return consequences
