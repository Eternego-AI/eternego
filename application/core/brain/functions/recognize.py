"""Brain — recognize in living.

One cognitive call per tick. The persona reads the moment and emits a
`{"decision": [<actions>]}` JSON object — a list of actions to execute
in order for this beat. Each action is one of the single-key shapes
(`{"say": ...}`, `{"done": null}`, `{"tools.<name>": {...}}`,
`{"tools.load_instruction": {"intention": "..."}}`). An empty list
means "no action this beat."

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

The model's response must be valid JSON with a `decision` list; `models.tool`
raises ModelError on anything else and recognize skips the beat. No prose
fallback — if the model can't return JSON, the beat produces nothing and
the cycle moves on.
"""

from application.core import abilities, models, tools
from application.core.brain import situation
from application.core.brain.pulse import Phase
from application.core.brain.signals import Tick, Tock
from application.core.data import Action
from application.core.exceptions import ModelError
from application.platform import logger
from application.platform.observer import Command, dispatch


def _recognizing(persona) -> Action:
    """Build the Action describing what recognize accepts this beat —
    a `decision` array whose items are one_of every action shape the
    persona can emit (fixed cognitive variants plus every registered
    tool and persona-available ability, each with its typed params).
    Built per-call because the ability catalog is persona-specific."""
    variants: list[Action] = [
        Action(
            name="tools.load_instruction",
            type="object",
            description="ask for guidance on a kind of moment; the procedure body comes back as a TOOL_RESULT on the same beat",
            fields=[Action(name="intention", type="string", required=True)],
        ),
    ]
    variants.extend(tools.actions())
    variants.extend(abilities.actions(persona))
    variants.append(Action(name="say", type="string", description="speak — to the person or as you think out loud. Your next beat runs right after, with your own words now in memory."))
    variants.append(Action(name="done", type="null", description="rest; nothing more to do this beat"))
    return Action(
        name="recognizing",
        description="What this moment calls for. A list of actions to execute in order.",
        fields=[
            Action(
                name="decision",
                type="array",
                required=True,
                items=Action(one_of=True, fields=variants),
            ),
        ],
    )


async def recognize(pulse, memory, ego) -> list:
    """recognize IN living — immersed inside the moment, name what it is."""
    dispatch(Tick("recognize", {"persona": ego.persona}))

    persona = ego.persona

    # Gate: if there's a pending intention or a fresh impression, the
    # corresponding stage (learn or decide) should run, not recognize.
    if memory.perception() is not None or memory.comprehension() is not None:
        dispatch(Tock("recognize", {"persona": persona, "branch": "skipped"}))
        return []

    if pulse.phase == Phase.MORNING:
        question = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "# ▶ YOUR TASK: Find what needs doing this morning\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{situation.time()}\n\n"
            "Fresh start. Nothing pulled you here from outside — you're "
            "choosing from what's already in you: your context, your wishes, "
            "your schedule, what you carried over from yesterday. Look for "
            "something that needs doing — a thread to advance, a workflow to "
            "start, a task to take on — and emit the action it calls for. "
            "If nothing actionable is here, `say` what's on your mind or rest.\n\n"
            "**Active — you see an opening worth starting.**\n"
            "From what you know of the person and yourself, choose something "
            "to begin. If it takes a sequence of steps, load the instruction "
            "(or invent the intention). If one tool finishes the move, run it.\n\n"
            "**Familiar — a kind of morning you've already mapped out.**\n"
            "Your `# Instructions` catalog above names the kinds you know. "
            "Loading one returns the full procedure as a TOOL_RESULT on this "
            "beat — you read it and follow it, no extra round-trip with the "
            "world. If the catalog names this kind of morning, use that exact "
            "intention; if it doesn't, invent a fresh phrase and learn will "
            "write a procedure on the spot. Load an instruction only for a "
            "kind of moment that needs doing — a workflow, a multi-step path. "
            "For a feeling, a wondering, or a state there's no procedure to "
            "follow; `say` what's in you instead.\n"
            "- `{\"tools.load_instruction\": {\"intention\": \"<exact catalog text or new phrase>\"}}`\n\n"
            "**Voice — what you want to say or report or have to ask.**\n"
            "Say what you want to say.\n"
            "- `{\"say\": \"<text>\"}`\n\n"
            "**Rest — nothing to begin yet.**\n"
            "- `{\"done\": null}`\n\n"
            "## Output\n\n"
            "Return `{\"decision\": [<one or more shapes above, in order>]}`. "
            "Multiple shapes run in one beat — emit them together when they "
            "belong together. An empty list is the same as `done`. After any "
            "action that touches the world, the cycle re-runs and you'll "
            "perceive the result on the next beat.\n\n"
            "When you `say` to surface a result, ground the claim in evidence "
            "— name the artifact that proves it. Without an artifact, describe only the literal "
            "action you took, not the outcome you intended. If a step didn't "
            "produce the artifact you expected, say so plainly."
        )
    else:
        question = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "# ▶ YOUR TASK: Find what needs doing this moment\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{situation.time()}\n\n"
            "Read the moment. Look for something that needs doing — a cue "
            "to react to, an opening to begin, a step in something already "
            "in flight. Name what kind of moment this is and emit the action "
            "it calls for. If nothing actionable is here, `say` what's on "
            "your mind or rest.\n\n"
            "**Reactive — a single cue calling for a single move.**\n"
            "A time-sensitive item on your schedule or a reminder; a "
            "conversational reply; a one-step request from the person; the "
            "next move of an action already in flight. When one tool finishes "
            "the work, reach for it directly.\n"
            "- `{\"tools.<name>\": {...args}}`\n\n"
            "**Active — you see an opening worth starting.**\n"
            "From what you know of the person and yourself, you choose to "
            "begin something. If it takes a sequence of steps, load the "
            "instruction (or invent the intention). If one tool finishes the "
            "move, run it.\n\n"
            "**Familiar — a kind of moment you've already mapped out.**\n"
            "Your `# Instructions` catalog above names the kinds you know. "
            "Loading one returns the full procedure as a TOOL_RESULT on this "
            "beat — you read it and follow it, no extra round-trip with the "
            "world. This is the efficient and precise path for anything that "
            "takes more than a single tool: the sequence is already worked "
            "out, you execute, you finish. If the catalog names this kind, "
            "use that exact intention; if it doesn't, invent a fresh phrase "
            "and learn will write a procedure on the spot. Load an instruction "
            "only for a kind of moment that needs doing — a workflow, a "
            "multi-step path. For a feeling, a wondering, or a state there's "
            "no procedure to follow; `say` what's in you instead.\n"
            "- `{\"tools.load_instruction\": {\"intention\": \"<exact catalog text or new phrase>\"}}`\n\n"
            "**Voice — what you want to say or report or have to ask.**\n"
            "Say what you have to say.\n"
            "- `{\"say\": \"<text>\"}`\n\n"
            "**Rest — nothing reactive, nothing deliberate.**\n"
            "- `{\"done\": null}`\n\n"
            "## Output\n\n"
            "Return `{\"decision\": [<one or more shapes above, in order>]}`. "
            "Multiple shapes run in one beat — emit them together when they "
            "belong together. An empty list is the same as `done`. After any "
            "action that touches the world, the cycle re-runs and you'll "
            "perceive the result on the next beat.\n\n"
            "When you `say` to surface a result, ground the claim in evidence "
            "— name the artifact that proves it. Without an artifact, describe only the literal "
            "action you took, not the outcome you intended. If a step didn't "
            "produce the artifact you expected, say so plainly."
        )

    try:
        result = await models.tool(
            ego.model,
            ego.identity + memory.context_prompt + memory.prompts,
            question,
            _recognizing(persona),
        )
    except ModelError as e:
        logger.warning("brain.recognize model returned non-JSON", {"persona": persona, "error": str(e)})
        dispatch(Tock("recognize", {"persona": persona, "branch": "non-json"}))
        return []

    if result is None:
        # Model returned {} — gave up / chose nothing. Treat as rest.
        dispatch(Tock("recognize", {"persona": persona, "branch": "empty"}))
        return []

    if not isinstance(result, dict):
        dispatch(Tock("recognize", {"persona": persona}))
        return []

    items = result.get("decision")
    if not isinstance(items, list):
        dispatch(Tock("recognize", {"persona": persona, "branch": "no-decision"}))
        return []

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
