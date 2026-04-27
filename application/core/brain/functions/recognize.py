"""Brain — recognize in living.

One cognitive call per tick. The persona reads the moment from inside it
and returns a single-key JSON object where the key names the action and
the value carries what it needs:

    {"tools.<name>": { ...args }}          — run a platform tool
    {"abilities.<name>": { ...args }}      — run a one-shot ability
    {"meanings.<name>": "<impression>"}    — recognize the situation, hand to decide
    {"done": null}                          — nothing to act on right now

`say`, `meanings`, `done` and prose are handled inline — recognize
dispatches them itself. `tools.<name>` and `abilities.<name>` are returned
as a capability list for clock's executor to run. The executor dispatches
the Event for each capability and persists the call+result pair to memory.

Meaning emissions set living.ego.memory.meaning + .impression so decide
takes over on this same beat. If the named meaning doesn't exist,
impression is kept and ability/meaning cleared — learn picks it up.

Done clears living.ego.memory.meaning; decide no-ops when there is no
meaning set, and reflect closes the tick.

If the model returns prose alongside a JSON action, the prose is dispatched
as a say (the persona's voice) and the action runs as its own step. If the
model returns prose with no JSON, the prose is dispatched as say and
troubleshooting is forced. A second prose response while already on
troubleshooting raises BrainException.
"""

from application.core import models
from application.core.agents import Living
from application.core.brain import situation
from application.core.brain.signals import Tick, Tock
from application.core.exceptions import BrainException, ModelError
from application.platform import logger
from application.platform.observer import Command, dispatch


async def recognize(living: Living) -> list:
    """recognize IN living — immersed inside the moment, name what it is."""
    dispatch(Tick("recognize", {"persona": living.ego.persona}))

    persona = living.ego.persona
    memory = living.ego.memory
    meaning_map = memory.meanings
    meaning_names = list(meaning_map.keys())

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Recognize what this moment calls for\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{situation.time()}\n\n"
        "This is a moment you can act. Considering your memory and the conversation, "
        "the act might be one of these:\n\n"
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
        "Return a single-key JSON object naming the action. Your tools, abilities, "
        "and meanings are all in your identity above — pick one by its full selector.\n\n"
        "- `{\"say\": \"<your message>\"}` — use your voice.\n"
        "- `{\"tools.<name>\": { ...args }}` — run a platform tool.\n"
        "- `{\"abilities.<name>\": { ...args }}` — run an ability.\n"
        "- `{\"meanings.<name>\": \"<your impression of the moment>\"}` — "
        "recognize the situation; decide takes it from there.\n"
        "- `{\"done\": null}` — rest.\n\n"
        "## Output\n\n"
        "Exactly one top-level key. Value shape: a string for say and "
        "meanings (text / impression), an args object for tools and "
        "abilities, null for done.\n\n"
        "Any prose outside the JSON will be sent to the person as a `say`."
    )

    try:
        prose, result = await models.chat_action(living.ego.model, living.ego.identity + living.pulse.hint() + memory.prompts, question)
    except ModelError as e:
        logger.info("brain.recognize chose prose, dispatching as say", {"persona": persona, "raw": e.raw})
        dispatch(Command("Persona wants to say", {"persona": persona, "text": e.raw}))
        if memory.meaning == "troubleshooting":
            logger.warning("brain.recognize refused while on troubleshooting — raising thinking fault", {"persona": persona})
            dispatch(Tock("recognize", {"persona": persona}))
            raise BrainException(
                "thinking model refused classification while on troubleshooting",
                model=living.ego.model,
            ) from e
        if "troubleshooting" in meaning_map:
            memory.impression = "could not classify the moment; forcing self-diagnosis"
            memory.meaning = "troubleshooting"
            memory.ability = meaning_names.index("troubleshooting") + 1
            logger.info("brain.recognize forcing troubleshooting after prose", {"persona": persona})
        else:
            memory.impression = ""
            memory.ability = 0
            memory.meaning = None
        dispatch(Tock("recognize", {"persona": persona}))
        return []

    if not isinstance(result, dict) or not result:
        memory.impression = ""
        memory.ability = 0
        memory.meaning = None
        dispatch(Tock("recognize", {"persona": persona}))
        return []

    # Prose around the JSON action is the persona's voice. Words after words
    # is the action itself; if the model wrote prose alongside its selector,
    # those words go to the person. The selector then runs as its own action.
    if prose:
        dispatch(Command("Persona wants to say", {"persona": persona, "text": prose}))
        logger.debug("brain.recognize dispatched prose as say", {"persona": persona, "prose_length": len(prose)})

    if len(result) > 1:
        logger.warning("brain.recognize returned multiple keys; using first", {"persona": persona, "keys": list(result.keys())})
    selector, value = next(iter(result.items()))
    selector = str(selector).strip()

    consequences: list = []

    if selector == "done":
        memory.impression = ""
        memory.meaning = None
        memory.ability = 0
        logger.debug("brain.recognize done", {"persona": persona})

    elif selector == "say":
        text = str(value) if value else ""
        if text:
            dispatch(Command("Persona wants to say", {"persona": persona, "text": text}))
            logger.debug("brain.recognize said", {"persona": persona, "text_length": len(text)})
        else:
            logger.debug("brain.recognize say with empty text; no-op", {"persona": persona})
        memory.impression = ""
        memory.meaning = None
        memory.ability = 0

    elif "." not in selector:
        logger.warning("brain.recognize unknown selector", {"persona": persona, "selector": selector})
        memory.impression = ""
        memory.meaning = None
        memory.ability = 0

    else:
        namespace, name = selector.split(".", 1)

        if namespace == "tools" or namespace == "abilities":
            args = value if isinstance(value, dict) else {}
            logger.debug("brain.recognize running capability", {"persona": persona, "selector": selector, "args": args})
            consequences.append({selector: args})
            memory.meaning = None
            memory.ability = 0

        elif namespace == "meanings":
            impression = str(value) if value else ""
            memory.impression = impression
            if name in meaning_map:
                memory.meaning = name
                memory.ability = meaning_names.index(name) + 1
                logger.debug("brain.recognize selected meaning", {"persona": persona, "meaning": name, "impression": impression})
            else:
                logger.info("brain.recognize named unknown meaning; leaving for learn", {"persona": persona, "named": name})
                memory.meaning = None
                memory.ability = 0

        else:
            logger.warning("brain.recognize unknown namespace", {"persona": persona, "namespace": namespace, "selector": selector})
            memory.impression = ""
            memory.meaning = None
            memory.ability = 0

    dispatch(Tock("recognize", {"persona": persona}))
    return consequences
