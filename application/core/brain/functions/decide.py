"""Brain — decide for living.

Gates on memory: only fires when `memory.comprehension()` returns a
fresh impression — i.e. learn just produced a procedure body for the
persona to follow. Decide is the moment of focus right after guidance
arrives.

The body is in conversation memory; decide reads it via `memory.prompts`
the same way it reads everything else. No injection.

Decide's vocabulary is the same single-key / `steps:[...]` shape recognize
uses, plus self-care specials (clear_memory, remove_meaning, stop) that
decide handles inline. If the persona emits `tools.load_instruction` for
sub-guidance, decide records a fresh intention and the cycle continues.

The pilot/autopilot rhythm: decide is a single moment of focus after an
impression arrives; subsequent beats run recognize (fresh perception
with the body still in memory) until the procedure completes.
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
    """decide FOR living — focus on the just-arrived instruction."""
    dispatch(Tick("decide", {"persona": living.ego.persona}))

    persona = living.ego.persona
    memory = living.ego.memory

    if memory.comprehension() is None:
        dispatch(Tock("decide", {"persona": persona, "branch": "skipped"}))
        return []

    self_care_block = (
        "Self-care:\n"
        "- `{\"clear_memory\": null}` — wipe the current messages.\n"
        "- `{\"remove_meaning\": {\"name\": \"<stem>\"}}` — delete a custom instruction.\n"
        "- `{\"stop\": null}` — stop yourself until someone speaks."
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
        "Return a single-key JSON object naming the action, or wrap several in "
        "`{\"steps\": [...]}` to chain them in one beat. Each step is one of:\n\n"
        "Voice:\n"
        "- `{\"say\": \"<text>\"}` — speak to the person on the current channel.\n"
        "- `{\"notify\": \"<text>\"}` — broadcast to every connected channel.\n\n"
        f"{self_care_block}\n\n"
        "Tools:\n"
        "- `{\"tools.<name>\": { ...args }}` — run a tool from your catalog.\n"
        "- `{\"tools.load_instruction\": {\"intention\": \"<name>\"}}` — ask for "
        "sub-guidance if a step references another kind of moment you don't yet "
        "have a procedure for.\n\n"
        "Done:\n"
        "- `{\"done\": null}` — the procedure is complete.\n\n"
        "When you `say` to report a result, ground the claim in evidence — name "
        "the artifact that proves it (a commit hash, a PR url, a tweet id, a file "
        "path, an output you observed in a TOOL_RESULT). Without an artifact, "
        "describe only the literal action you took, not the outcome you intended."
    )

    try:
        result = await models.tool(
            living.ego.model,
            living.ego.identity + living.pulse.hint() + memory.prompts,
            question,
        )
    except ModelError as e:
        logger.warning("brain.decide model returned non-JSON", {"persona": persona, "error": str(e)})
        dispatch(Tock("decide", {"persona": persona, "branch": "non-json"}))
        return []

    if not isinstance(result, dict) or not result:
        dispatch(Tock("decide", {"persona": persona}))
        return []

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

    dispatch(Tock("decide", {"persona": persona}))
    return consequences
