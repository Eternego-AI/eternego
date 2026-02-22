"""Consent abilities — permission checking, requesting, and resolving."""

from application.platform import logger
from application.core.data import Channel, Persona, Prompt, Thread
from application.core.brain.abilities._base import ability


@ability(
"Check if you have permission for an action before proceeding. Items: [action description]",
["commander"],
order=3)
async def check_permission(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Look up stored permissions and return what is known for each action."""
    logger.info("Ability: check_permission", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    try:
        from application.core.brain import consent
        parts = []
        for action in items:
            result = consent.check(persona, str(action))
            if result == "granted":
                parts.append(f"Permission granted: {action}")
            elif result == "denied":
                parts.append(f"Permission denied: {action}")
            else:
                parts.append(f"No permission record for: {action} — use ask_permission to request it")
        return Prompt(role="user", content="\n".join(parts))
    except Exception:
        return Prompt(role="user", content="Could not check permissions. Treat the action as unpermitted and ask the person directly before proceeding.")


@ability(
"Ask the person for permission before taking a sensitive action. Items: [action description]",
["commander"],
order=4)
async def ask_permission(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Record the permission request and ask the person. Reasoning stops until resolve_permission resumes it."""
    logger.info("Ability: ask_permission", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    try:
        from application.core.brain import consent
        from application.core.brain.abilities.communication import say
        actions = [str(item) for item in items]
        for action in actions:
            consent.request(persona, action, thread.id)

        if len(actions) == 1:
            question = f"May I {actions[0]}?"
        else:
            listed = "\n".join(f"- {a}" for a in actions)
            question = f"May I do the following?\n{listed}"

        await say(persona, thread, channel, [question])
        return Prompt(role="user", content="Permission requested. Waiting for the person's response before continuing.")
    except Exception:
        return Prompt(role="user", content="Could not record the permission request. Proceed as if the person has not yet answered — use say to ask them directly and wait for their reply before acting.")


@ability(
"Record the person's permission decision (granted or denied) and resume the waiting thread. Items: [{action, decision, statement}]",
["commander"],
order=5)
async def resolve_permission(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Record the permission decision and resume the original reasoning thread."""
    logger.info("Ability: resolve_permission", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    try:
        from application.core.brain import mind, consent
        from application.core.brain import memories as mem
        from application.core.data import Thread as T
        m = mem.agent(persona)
        outcomes = []
        for item in items:
            action = item.get("action", "")
            decision = item.get("decision", "")
            statement = item.get("statement", "")
            original_thread_id = consent.resolve(persona, action, decision, statement)
            if not original_thread_id:
                continue
            original_thread = T(id=original_thread_id)
            m.remember_on(original_thread, {"role": "user", "content": f"Permission {decision}: {statement}"})
            mind.think(persona, original_thread, channel)
            outcomes.append(f"Permission {decision}: {action}")
        if not outcomes:
            return None
        return Prompt(role="user", content="\n".join(outcomes))
    except Exception:
        return Prompt(role="user", content="Could not record the permission decision. The waiting task will not resume automatically — let the person know and ask them to repeat their instruction so you can act on it directly.")
