"""Brain — decide for living.

Gates on memory: only fires when `memory.comprehension()` returns a
fresh impression — i.e. learn just produced a procedure body for the
persona to follow. Decide is the moment of focus right after guidance
arrives.

The body is in conversation memory; decide reads it via `memory.prompts`
the same way it reads everything else. No injection.

Decide's vocabulary is the same `{"decision": [<actions>]}` shape
recognize uses, plus self-care specials (notify, clear_memory,
remove_meaning, stop) that decide handles inline. If the persona emits
`tools.load_instruction` for sub-guidance, decide records a fresh
intention and the cycle continues.

The pilot/autopilot rhythm: decide is a single moment of focus after an
impression arrives; subsequent beats run recognize (fresh perception
with the body still in memory) until the procedure completes.
"""

from application.core import abilities, models, paths, tools
from application.core.agents import Living
from application.core.brain import situation
from application.core.brain.signals import Tick, Tock
from application.core.data import Action, Message, Prompt
from application.core.exceptions import ModelError
from application.platform import logger
from application.platform.observer import Command, dispatch


def _deciding(persona) -> Action:
    """Build the Action describing what decide accepts this beat — same
    structure as recognize but with decide's extra cognitive variants
    (notify, clear_memory, stop, remove_meaning) in the items oneOf."""
    variants: list[Action] = [
        Action(
            name="tools.load_instruction",
            type="object",
            description="ask for sub-guidance on another kind of moment",
            fields=[Action(name="intention", type="string", required=True)],
        ),
        Action(name="clear_memory", type="null", description="wipe out your current running memory — for when memory crashes"),
        Action(name="stop", type="null", description="stop your service until the person restarts you — for unexpected malfunctioning"),
        Action(
            name="remove_meaning",
            type="object",
            description="delete a custom instruction by its stem",
            fields=[Action(name="name", type="string", required=True)],
        ),
    ]
    variants.extend(tools.actions())
    variants.extend(abilities.actions(persona))
    variants.append(Action(name="notify", type="string", description="broadcast to every connected channel"))
    variants.append(Action(name="say", type="string", description="speak this round and ONLY speak; if you want to act AND speak, use tools.report paired with the action instead"))
    variants.append(Action(name="done", type="null", description="the procedure is complete"))
    return Action(
        name="deciding",
        description="The next action(s) of the procedure you are following. A list of actions to execute in order.",
        fields=[
            Action(
                name="decision",
                type="array",
                required=True,
                items=Action(one_of=True, fields=variants),
            ),
        ],
    )


async def decide(living: Living) -> list:
    """decide FOR living — focus on the just-arrived instruction."""
    dispatch(Tick("decide", {"persona": living.ego.persona}))

    persona = living.ego.persona
    memory = living.ego.memory

    comprehension = memory.comprehension()
    if comprehension is None:
        dispatch(Tock("decide", {"persona": persona, "branch": "skipped"}))
        return []

    self_care_block = (
        "Self-care:\n"
        "- `{\"clear_memory\": null}` — wipe out your current running memory; for when memory crashes.\n"
        "- `{\"remove_meaning\": {\"name\": \"<stem>\"}}` — delete a custom instruction.\n"
        "- `{\"stop\": null}` — stop your service until the person restarts you; for unexpected malfunctioning."
    )

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Focus on the last instruction\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{situation.time()}\n\n"
        "You just received an instruction. The procedure body is in your most "
        "recent TOOL_RESULT — read it and follow the procedure.\n\n"
        "If the procedure has multiple steps, pay attention to the conversation "
        "to see which step you are on and continue from there.\n\n"
        "## Output\n\n"
        "Return a JSON object with a single `decision` key — a list of actions to "
        "execute in order for this beat. Each action in the list is one of the "
        "single-key shapes below. If the procedure is complete with nothing to do "
        "this beat, return `{\"decision\": []}` or include `{\"done\": null}`.\n\n"
        "Tools:\n"
        "- `{\"tools.<name>\": { ...args }}` — run a tool from your catalog.\n"
        "- `{\"tools.load_instruction\": {\"intention\": \"<name>\"}}` — ask for "
        "sub-guidance if a step references another kind of moment you don't yet "
        "have a procedure for.\n\n"
        f"{self_care_block}\n\n"
        "Voice — only when you have nothing to do but speak:\n"
        "- `{\"say\": \"<text>\"}` — speak this round and ONLY speak. Use this only "
        "if there is no action left to take this beat. If you want to say something "
        "WHILE acting (or alongside another action), use `tools.report` paired with "
        "the action in the same decision list — never `say` for narrating intent. "
        "Saying instead of acting is the most common error here.\n"
        "- `{\"notify\": \"<text>\"}` — broadcast to every connected channel.\n\n"
        "Done:\n"
        "- `{\"done\": null}` — the procedure is complete. Equivalent to an empty "
        "decision list.\n\n"
        "When you `say` or `tools.report` to surface a result, ground the claim in "
        "evidence — name the artifact that proves it (a commit hash, a PR url, a "
        "tweet id, a file path, an output you observed in a TOOL_RESULT). Without "
        "an artifact, describe only the literal action you took, not the outcome "
        "you intended."
    )

    try:
        result = await models.tool(
            living.ego.model,
            living.ego.identity + living.pulse.hint() + memory.prompts,
            question,
            _deciding(persona),
        )
    except ModelError as e:
        logger.warning("brain.decide model returned non-JSON", {"persona": persona, "error": str(e)})
        dispatch(Tock("decide", {"persona": persona, "branch": "non-json", "comprehension": comprehension}))
        return []

    if result is None:
        # Model returned {} — gave up. Treat as rest.
        dispatch(Tock("decide", {"persona": persona, "branch": "empty", "comprehension": comprehension}))
        return []

    if not isinstance(result, dict):
        dispatch(Tock("decide", {"persona": persona, "comprehension": comprehension}))
        return []

    items = result.get("decision")
    if not isinstance(items, list):
        dispatch(Tock("decide", {"persona": persona, "branch": "no-decision", "comprehension": comprehension}))
        return []

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
                    intention_to_stem = paths.read_json(paths.learned(persona.id)) or {}
                    intention_to_stem = {i: s for i, s in intention_to_stem.items() if s != name}
                    paths.save_as_json(persona.id, paths.learned(persona.id), intention_to_stem)
                    result_text = f"removed instruction: {name}"
                else:
                    status, result_text = "error", f"instruction not found: {name}"
            memory.add_tool_result("remove_meaning", value, status, result_text)

        elif selector == "stop":
            dispatch(Command("Persona requested stop", {"persona": persona}))

        elif selector == "tools.load_instruction":
            # Cognitive sub-call: record a fresh intention. Learn fires
            # next, produces the matching impression on the same iteration.
            args = value if isinstance(value, dict) else {}
            text = str(args.get("intention", "")).strip()
            if text:
                memory.intention(text)
                logger.debug("brain.decide expressed sub-intention", {"persona": persona, "intention": text[:120]})

        elif "." in selector:
            namespace, _name = selector.split(".", 1)
            if namespace == "tools":
                args = value if isinstance(value, dict) else {}
                consequences.append({selector: args})
            else:
                logger.warning("brain.decide unknown namespace", {"persona": persona, "namespace": namespace, "selector": selector})

        else:
            logger.warning("brain.decide unknown selector", {"persona": persona, "selector": selector})

    dispatch(Tock("decide", {"persona": persona, "comprehension": comprehension}))
    return consequences
