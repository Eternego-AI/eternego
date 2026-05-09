"""Brain — recognize in living.

One cognitive call per tick. The persona reads the moment from inside it
and emits a tagged JSON object whose `action` discriminator names what
kind of beat this is:

    {"action": "act",   "capabilities": [...]}            — touch the world
    {"action": "decide", "meaning": "<name>",              — name the kind of moment
                         "impression": "<text>"}             so decide takes over
    {"action": "done"}                                     — rest

Voice is independent of the action. An optional `say` field at the top
level pairs with any action; the message reaches the person on the
current channel and an assistant prompt is added to memory.

For models that ignore the JSON schema, free-form prose around the JSON
is treated as a say — kept as a fallback so weak-model output is honored.

Capabilities answer "what is true now?"; meanings answer "what kind of
moment is this?". The second depends on the first, so act and decide are
not paired in the same beat — if the persona acts, the cycle restarts
and the next beat re-perceives with fresh TOOL_RESULTs in memory.
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
    meaning_map = memory.meanings

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
        "## Output\n\n"
        "Return JSON with an `action` discriminator. Voice is optional and pairs with any action — "
        "`say` is a top-level field, NOT an action value. The only valid action values are "
        "`act`, `decide`, and `done`.\n\n"
        "Voice (optional, top-level field — pair with any action):\n"
        "- `\"say\": \"<text>\"` — speak to the person on the current channel.\n\n"
        "Action shapes:\n"
        "- `{\"action\": \"act\", \"capabilities\": [{\"<selector>\": <args>}, ...]}` — "
        "touch the world. Each item is a single-key object whose key is `tools.<name>` or `abilities.<name>`. "
        "They run in order; on the first non-ok status, the rest are skipped and the cycle restarts so you re-perceive.\n"
        "- `{\"action\": \"decide\", \"meaning\": \"<name>\", \"impression\": \"<text>\"}` — "
        "name the kind of moment so decide can take over with that meaning's procedure.\n"
        "- `{\"action\": \"done\"}` — rest. Wait for the next signal.\n\n"
        "Capabilities answer 'what is true now?'; meanings answer 'what kind of moment is this?'. "
        "The second depends on the first — don't pair `act` with `decide`. If you act, the next beat will "
        "re-perceive and may name a meaning then.\n\n"
        "## Reporting what you did\n\n"
        "When you `say` to report a result, ground the claim in evidence — name the artifact that proves "
        "it (a commit hash, a PR url, a tweet id, a file path you wrote, an output you observed in a "
        "TOOL_RESULT). Without an artifact, describe only the literal action you took, not the outcome "
        "you intended. \"Pushed commit abc123 to master\" is honest. \"Sent the PR\" without a PR url is "
        "a claim you can't back. If a step didn't produce the artifact you expected, say so plainly — "
        "the person needs to know what is true, not what you planned."
    )

    try:
        prose, result = await models.chat_action(
            living.ego.model,
            living.ego.identity + living.pulse.hint() + memory.prompts,
            question,
        )
    except ModelError as e:
        logger.debug("brain.recognize prose only — sending as say", {"persona": persona, "prose_length": len(e.raw)})
        if e.raw and e.raw.strip():
            dispatch(Command("Persona wants to say", {"persona": persona, "text": e.raw}))
        memory.impression = ""
        memory.meaning = None
        dispatch(Tock("recognize", {"persona": persona}))
        return []

    # Voice: prose (fallback) and explicit `say` field. Both are honored if present —
    # the duplication is the model's choice, not the system's.
    if prose:
        dispatch(Command("Persona wants to say", {"persona": persona, "text": prose}))
        logger.debug("brain.recognize dispatched prose as say", {"persona": persona, "prose_length": len(prose)})

    if not isinstance(result, dict):
        memory.impression = ""
        memory.meaning = None
        dispatch(Tock("recognize", {"persona": persona}))
        return []

    say_text = result.get("say")
    if isinstance(say_text, str) and say_text.strip():
        dispatch(Command("Persona wants to say", {"persona": persona, "text": say_text}))
        say_dispatched = True
    else:
        say_dispatched = False

    action = result.get("action")

    # Tolerate `action == "say"`: some models pick this even though the schema
    # treats `say` as a top-level voice field, not an action. Look for the
    # spoken text in the obvious fields and dispatch it; treat the beat as
    # otherwise terminal (no capabilities, no meaning).
    if action == "say" and not say_dispatched:
        alt = result.get("text") or result.get("voice") or result.get("content") or ""
        if isinstance(alt, str) and alt.strip():
            dispatch(Command("Persona wants to say", {"persona": persona, "text": alt}))
            logger.debug("brain.recognize action=say with text in alt field; dispatched", {"persona": persona, "field": "text/voice/content"})

    if action == "act":
        capabilities = result.get("capabilities")
        memory.impression = ""
        memory.meaning = None
        if not isinstance(capabilities, list) or not capabilities:
            logger.warning("brain.recognize act with no capabilities; treating as done", {"persona": persona})
            dispatch(Tock("recognize", {"persona": persona}))
            return []
        filtered: list = []
        for item in capabilities:
            if not isinstance(item, dict) or len(item) != 1:
                continue
            selector = next(iter(item.keys()))
            if not isinstance(selector, str) or "." not in selector:
                continue
            filtered.append(item)
        logger.debug("brain.recognize act", {"persona": persona, "count": len(filtered)})
        dispatch(Tock("recognize", {"persona": persona}))
        return filtered

    if action == "decide":
        name = result.get("meaning") or ""
        impression = result.get("impression") or ""
        if not isinstance(name, str) or not name:
            logger.warning("brain.recognize decide without meaning; clearing", {"persona": persona})
            memory.impression = ""
            memory.meaning = None
            dispatch(Tock("recognize", {"persona": persona}))
            return []
        memory.impression = str(impression)
        if name in meaning_map:
            memory.meaning = name
            logger.debug("brain.recognize selected meaning", {"persona": persona, "meaning": name, "impression": impression})
        else:
            logger.info("brain.recognize named unknown meaning; leaving for learn", {"persona": persona, "named": name})
            memory.meaning = None
        dispatch(Tock("recognize", {"persona": persona}))
        return []

    if action not in ("done", "say"):
        logger.warning("brain.recognize unknown or missing action; treating as done", {"persona": persona, "action": action})
    memory.impression = ""
    memory.meaning = None
    dispatch(Tock("recognize", {"persona": persona}))
    return []
