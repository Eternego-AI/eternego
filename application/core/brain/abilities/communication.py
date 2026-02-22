"""Communication abilities — sending messages and starting conversations."""

from application.platform import logger, processes
from application.core.data import Channel, Persona, Prompt, Thread
from application.core.brain.abilities._base import ability


@ability(
"Send a message to the person on their active channel. Items: [message text]",
["commander", "conversational"],
order=1)
async def say(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Send a message on the channel and record it in memory."""
    logger.info("Ability: say", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from application.core import channels as ch_module
    from application.core.brain import memories as mem
    m = mem.agent(persona)
    for text in items:
        text = str(text)
        if channel.authority == "conversational":
            import json
            payload = {"choices": [{"message": {"role": "assistant", "content": text}}]}
            await ch_module.send(channel, json.dumps(payload))
        else:
            await ch_module.send(channel, text)
        m.remember_on(thread, {"role": "assistant", "content": text})
    return None


@ability(
"Ask the person a clarifying question before proceeding. Items: [question]",
["commander", "conversational"],
order=9)
async def clarify(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Send a clarifying question and stop reasoning until the person responds."""
    logger.info("Ability: clarify", {"persona": persona.id, "thread": thread.id, "channel": channel.name})

    async def _run():
        await say(persona, thread, channel, items)

    processes.run_async(_run)
    return None


@ability(
"Escalate questions to a more capable frontier model. Items: [question]",
["commander", "conversational"],
order=10)
async def escalate(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Ask the frontier model and return its answer as context."""
    logger.info("Ability: escalate", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from application.core import frontier
    if not persona.frontier:
        return Prompt(role="user", content="No frontier model is configured. Be honest with the person — acknowledge you are not confident enough to handle this well, and let them know that having a more capable model available would help.")
    answers = [await frontier.respond(persona.frontier, str(item)) for item in items]
    return Prompt(role="user", content="Frontier answers:\n" + "\n".join(answers))


@ability(
"Start a new conversation thread for an unrelated incoming message. Items: [message]",
["commander"],
order=17)
async def start_conversation(persona: Persona, thread: Thread, channel: Channel, items: list) -> None:
    """Remove items from the current thread, start a fresh thread per item, and begin reasoning."""
    logger.info("Ability: start_conversation", {"persona": persona.id, "thread": thread.id, "channel": channel.name})

    async def _run():
        from application.core.brain import mind
        from application.core.brain import memories as mem
        m = mem.agent(persona)
        for item in items:
            m.remove_from_thread(str(item), thread.id)
            m.new_thread()
            new_thread = m.remember({"role": "user", "content": str(item)})
            mind.think(persona, new_thread, channel)

    processes.run_async(_run)
