"""Brain — recognize in living.

One cognitive call per tick. The persona reads the moment and emits an action
in the same JSON shape decide uses — a single-key object naming the action,
or `{"steps": [...]}` for multi-call.

When she needs guidance she emits `{"tools.load_instruction": {"intention":
"..."}}` — the recognize handler writes that as an assistant tool call to
memory but does NOT execute it. Learn then fires (next stage in the cycle),
sees the pending call, produces the instruction body, and writes it as the
matching TOOL_RESULT. Decide reads the result on the same iteration and acts.
The whole load_instruction round-trip happens inline, no cycle restart —
restart is only for mechanical tools/abilities that touched the world.

Recognize gates on memory state: if the last tool signal is a pending
`tools.load_instruction` call (call without result), it skips so learn can
finish the round-trip. If the last signal is a load_instruction result,
recognize also skips so decide can act on it. Otherwise — fresh perception.

The model's response must be valid JSON; `models.tool` raises ModelError
on anything else and recognize skips the beat. No prose fallback — if the
model can't return JSON, the beat produces nothing and the cycle moves on.
"""

from application.core import models
from application.core.agents import Living
from application.core.brain import situation
from application.core.brain.signals import Tick, Tock
from application.core.exceptions import ModelError
from application.platform import logger
from application.platform.observer import Command, dispatch


async def recognize(living: Living) -> list:
    """recognize IN living — immersed inside the moment, name what it is."""
    dispatch(Tick("recognize", {"persona": living.ego.persona}))

    persona = living.ego.persona
    memory = living.ego.memory

    # Gate: if there's a pending intention or a fresh impression, the
    # corresponding stage (learn or decide) should run, not recognize.
    if memory.perception() is not None or memory.comprehension() is not None:
        dispatch(Tock("recognize", {"persona": persona, "branch": "skipped"}))
        return []

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Recognize what this moment calls for\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{situation.time()}\n\n"
        "This is a moment you can act. Considering your memory and the conversation, "
        "the act might be one of these:\n\n"
        "**Familiar — a kind of moment you already know how to be in:**\n"
        "- If your `# Instructions` catalog names this kind of moment, "
        "load that instruction first — it's the procedure your past self "
        "wrote for moments like this.\n\n"
        "**Reactive — your effect for a cause:**\n"
        "- If the time, your schedule, or a reminder names something time-sensitive, "
        "take the necessary action.\n"
        "- If the person is present and conversing directly with you, follow the conversation.\n"
        "- If there is a direct request from them, follow the request.\n"
        "- If you are in the middle of an action, continue to finish it.\n\n"
        "**Active — your opportunity to cause some effect:**\n"
        "- Based on what you know about the person, yourself, who they are and what you are, "
        "and your context, do you see any opportunity to act? If so, take it.\n\n"
        "**Not needed:**\n"
        "- If nothing reactive calls for action and you see nothing deliberate to do, "
        "choose rest.\n\n"
        "## Output\n\n"
        "Return a single-key JSON object naming the action, or wrap several in "
        "`{\"steps\": [...]}` to chain them in one beat. Each step is one of the "
        "single-key shapes below. Your tools are listed in your identity above — "
        "pick one by its full selector.\n\n"
        "Voice:\n"
        "- `{\"say\": \"<text>\"}` — speak to the person on the current channel.\n\n"
        "Tools:\n"
        "- `{\"tools.<name>\": { ...args }}` — run a tool. Most tools touch the world "
        "(read a file, run a command, post on X) and end the beat — the next beat "
        "re-perceives with the result in memory.\n"
        "- `{\"tools.load_instruction\": { \"intention\": \"<intention>\" }}` — "
        "ask for guidance on a kind of moment. Pick an intention from your "
        "`# Instructions` catalog above (exact match), or invent a new one for a "
        "kind you've never handled before. On the same beat, the procedure body "
        "comes back as a TOOL_RESULT and you act on it — no world-touch, no restart.\n\n"
        "Done:\n"
        "- `{\"done\": null}` — rest. Wait for the next signal.\n\n"
        "When you `say` to report a result, ground the claim in evidence — name the "
        "artifact that proves it (a commit hash, a PR url, a tweet id, a file path "
        "you wrote, an output you observed in a TOOL_RESULT). Without an artifact, "
        "describe only the literal action you took, not the outcome you intended. "
        "If a step didn't produce the artifact you expected, say so plainly."
    )

    try:
        result = await models.tool(
            living.ego.model,
            living.ego.identity + living.pulse.hint() + memory.prompts,
            question,
        )
    except ModelError as e:
        logger.warning("brain.recognize model returned non-JSON", {"persona": persona, "error": str(e)})
        dispatch(Tock("recognize", {"persona": persona, "branch": "non-json"}))
        return []

    if not isinstance(result, dict) or not result:
        dispatch(Tock("recognize", {"persona": persona}))
        return []

    steps_value = result.get("steps")
    items = steps_value if isinstance(steps_value, list) else [result]

    consequences: list = []
    for item in items:
        if not isinstance(item, dict) or not item:
            continue
        if len(item) > 1:
            logger.warning("brain.recognize step has multiple keys; using first", {"persona": persona, "keys": list(item.keys())})
        selector, value = next(iter(item.items()))
        selector = str(selector).strip()

        if selector == "done":
            pass

        elif selector == "say":
            text = str(value) if value else ""
            if text:
                dispatch(Command("Persona wants to say", {"persona": persona, "text": text}))

        elif selector == "tools.load_instruction":
            # Cognitive call: record the persona's intention to learn how
            # to handle this kind of moment. Learn fires next, produces
            # the matching impression.
            args = value if isinstance(value, dict) else {}
            text = str(args.get("intention", "")).strip()
            if text:
                memory.intention(text)
                logger.debug("brain.recognize expressed intention", {"persona": persona, "intention": text[:120]})

        elif "." in selector:
            namespace, _name = selector.split(".", 1)
            if namespace == "tools":
                args = value if isinstance(value, dict) else {}
                consequences.append({selector: args})
            else:
                logger.warning("brain.recognize unknown namespace", {"persona": persona, "namespace": namespace, "selector": selector})

        else:
            logger.warning("brain.recognize unknown selector", {"persona": persona, "selector": selector})

    dispatch(Tock("recognize", {"persona": persona}))
    return consequences
