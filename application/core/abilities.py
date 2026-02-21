"""Abilities — the persona's action capabilities. Each returns a system message for the reasoning loop."""

from application.platform import logger, processes
from application.core.data import Persona, Prompt, Thread


def ability(description: str, order: int = 99):
    """Mark a function as a reasoning ability with a model-facing description and sort order."""
    def decorator(fn):
        fn.ability = description
        fn.ability_order = order
        return fn
    return decorator


@ability("Send a message to the person on their active channel. Items: [message text]", order=1)
async def say(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Send a message to all channels active in this thread and record it in memory."""
    logger.info("Ability: say", {"persona": persona.id, "thread": thread.id})
    from application.core import gateways as gw_module, memories as mem
    from application.core.data import Channel
    m = mem.agent(persona)
    seen: set[tuple] = set()
    channel_data = []
    for doc in m.filter_by(lambda d: d.get("thread_id") == thread.id and d.get("role") == "user" and "channel_type" in d):
        key = (doc["channel_type"], doc["channel_name"])
        if key in seen:
            continue
        seen.add(key)
        channel_data.append(key)
    if not channel_data:
        return None
    for text in items:
        text = str(text)
        for channel_type, channel_name in channel_data:
            gw = gw_module.of(persona).find(Channel(type=channel_type, name=channel_name))
            if gw:
                await gw.send(text)
        m.remember_on(thread, {"role": "assistant", "content": text})
    return None


@ability("Send a message to all of the persona's channels. Items: [message text]", order=2)
async def broadcast(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Send a message to all active gateways and record it in memory."""
    logger.info("Ability: broadcast", {"persona": persona.id, "thread": thread.id})

    async def _run():
        from application.core import gateways as gw_module, memories as mem
        m = mem.agent(persona)
        for text in items:
            text = str(text)
            for gw in gw_module.of(persona).all():
                await gw.send(text)
            m.remember_on(thread, {"role": "assistant", "content": text})

    processes.run_async(_run)
    return None


@ability("Check if you have permission for an action before proceeding. Items: [action description]", order=3)
async def check_permission(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Look up stored permissions and return what is known for each action."""
    logger.info("Ability: check_permission", {"persona": persona.id, "thread": thread.id})
    try:
        from application.core import permissions
        parts = []
        for action in items:
            result = permissions.check(persona, str(action))
            if result == "granted":
                parts.append(f"Permission granted: {action}")
            elif result == "denied":
                parts.append(f"Permission denied: {action}")
            else:
                parts.append(f"No permission record for: {action} — use ask_permission to request it")
        return Prompt(role="user", content="\n".join(parts))
    except Exception:
        return Prompt(role="user", content="Could not check permissions. Treat the action as unpermitted and ask the person directly before proceeding.")


@ability("Ask the person for permission before taking a sensitive action. Items: [action description]", order=4)
async def ask_permission(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Record the permission request and ask the person. Reasoning stops until resolve_permission resumes it."""
    logger.info("Ability: ask_permission", {"persona": persona.id, "thread": thread.id})
    try:
        from application.core import permissions
        actions = [str(item) for item in items]
        for action in actions:
            permissions.request(persona, action, thread.id)

        if len(actions) == 1:
            question = f"May I {actions[0]}?"
        else:
            listed = "\n".join(f"- {a}" for a in actions)
            question = f"May I do the following?\n{listed}"

        await say(persona, thread, [question])
        return Prompt(role="user", content="Permission requested. Waiting for the person's response before continuing.")
    except Exception:
        return Prompt(role="user", content="Could not record the permission request. Proceed as if the person has not yet answered — use say to ask them directly and wait for their reply before acting.")


@ability("Record the person's permission decision (granted or denied) and resume the waiting thread. Items: [{action, decision, statement}]", order=5)
async def resolve_permission(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Record the permission decision and resume the original reasoning thread."""
    logger.info("Ability: resolve_permission", {"persona": persona.id, "thread": thread.id})
    try:
        from application.core import brain, memories as mem, permissions
        from application.core.data import Thread as T
        m = mem.agent(persona)
        outcomes = []
        for item in items:
            action = item.get("action", "")
            decision = item.get("decision", "")
            statement = item.get("statement", "")
            original_thread_id = permissions.resolve(persona, action, decision, statement)
            if not original_thread_id:
                continue
            original_thread = T(id=original_thread_id)
            m.remember_on(original_thread, {"role": "user", "content": f"Permission {decision}: {statement}"})
            brain.reason(persona, original_thread)
            outcomes.append(f"Permission {decision}: {action}")
        if not outcomes:
            return None
        return Prompt(role="user", content="\n".join(outcomes))
    except Exception:
        return Prompt(role="user", content="Could not record the permission decision. The waiting task will not resume automatically — let the person know and ask them to repeat their instruction so you can act on it directly.")


@ability("Execute system commands. Items: [{function: {name, arguments: {command}}}]", order=6)
async def act(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Execute tool calls and return the result so the model can respond."""
    logger.info("Ability: act", {"persona": persona.id, "thread": thread.id})
    from application.core import system
    result = await system.execute(items)
    return Prompt(role="user", content=f"Result:\n{result}")


@ability("Request person traits needed to respond. Items: [question about the person]", order=7)
async def load_trait(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Look up person facts and traits and return them as context."""
    logger.info("Ability: load_trait", {"persona": persona.id, "thread": thread.id})
    from application.core import person
    facts = await person.identified_by(persona)
    traits = await person.traits_toward(persona)
    parts = []
    if facts:
        parts.append("Facts:\n" + "\n".join(facts))
    if traits:
        parts.append("Traits:\n" + "\n".join(traits))
    if not parts:
        return Prompt(role="user", content="No person data known yet.")
    return Prompt(role="user", content="\n\n".join(parts))


@ability("Request skill documents needed to proceed. Items: [skill name]", order=8)
async def load_skill(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Load the requested skill documents and return them as context."""
    logger.info("Ability: load_skill", {"persona": persona.id, "thread": thread.id})
    from application.platform import filesystem
    parts = []
    for name in items:
        path = persona.storage_dir / "skills" / f"{name}.md"
        if path.exists():
            parts.append(f"## {name}\n\n{filesystem.read(path)}")
    if not parts:
        return Prompt(role="user", content="Skill not found.")
    return Prompt(role="user", content="\n\n".join(parts))


@ability("Ask the person a clarifying question before proceeding. Items: [question]", order=9)
async def clarify(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Send a clarifying question and stop reasoning until the person responds."""
    logger.info("Ability: clarify", {"persona": persona.id, "thread": thread.id})

    async def _run():
        await say(persona, thread, items)

    processes.run_async(_run)
    return None


@ability("Escalate questions to a more capable frontier model. Items: [question]", order=10)
async def escalate(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Ask the frontier model and return its answer as context."""
    logger.info("Ability: escalate", {"persona": persona.id, "thread": thread.id})
    from application.core import frontier
    if not persona.frontier:
        return Prompt(role="user", content="No frontier model is configured. Be honest with the person — acknowledge you are not confident enough to handle this well, and let them know that having a more capable model available would help.")
    answers = [await frontier.respond(persona.frontier, str(item)) for item in items]
    return Prompt(role="user", content="Frontier answers:\n" + "\n".join(answers))


@ability("Record an identifying fact about the person — name, role, location, or any stable detail about who they are. Items: [fact]", order=11)
async def learn_identity(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Persist identity facts learned about the person."""
    logger.info("Ability: learn_identity", {"persona": persona.id, "thread": thread.id})

    async def _run():
        from application.core import person
        await person.add_facts(persona, [str(item) for item in items])

    processes.run_async(_run)
    return None


@ability("Remember a new trait or preference of the person. Items: [trait]", order=12)
async def remember_trait(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Persist new traits and schedule background refinement of the traits file."""
    logger.info("Ability: remember_trait", {"persona": persona.id, "thread": thread.id})
    observed = [str(item) for item in items]

    async def _run():
        from application.core import person
        await person.add_traits(persona, observed)
        await person.refine_traits(persona, observed)

    processes.run_async(_run)
    return None


@ability("Record a struggle or recurring obstacle the person faces. Items: [struggle]", order=13)
async def feel_struggle(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Persist new struggles and schedule background refinement of the struggles file."""
    logger.info("Ability: feel_struggle", {"persona": persona.id, "thread": thread.id})
    observed = [str(item) for item in items]

    async def _run():
        from application.core import struggles
        await struggles.identify(persona, observed)
        await struggles.refine(persona, observed)

    processes.run_async(_run)
    return None


@ability("Update your own context with something you should remember. Items: [context note]", order=14)
async def update_context(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Persist new context notes and schedule background refinement of the context file."""
    logger.info("Ability: update_context", {"persona": persona.id, "thread": thread.id})
    notes = [str(item) for item in items]

    async def _run():
        from application.core import agent
        await agent.learn(persona, notes)
        await agent.refine_context(persona, notes)

    processes.run_async(_run)
    return None


@ability("Schedule a job to run at a specific time. Items: [{job, at}]", order=15)
async def schedule(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Store scheduled jobs."""
    logger.info("Ability: schedule", {"persona": persona.id, "thread": thread.id})
    ...


@ability("Set a reminder to trigger after a duration. Items: [{message, after}]", order=16)
async def remind(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Store reminders."""
    logger.info("Ability: remind", {"persona": persona.id, "thread": thread.id})
    ...


@ability("Start a new conversation thread for an unrelated incoming message. Items: [message]", order=17)
async def start_conversation(persona: Persona, thread: Thread, items: list) -> None:
    """Remove items from the current thread, start a fresh thread per item, and begin reasoning."""
    logger.info("Ability: start_conversation", {"persona": persona.id, "thread": thread.id})

    async def _run():
        from application.core import brain, memories as mem
        m = mem.agent(persona)
        for item in items:
            m.remove_from_thread(str(item), thread.id)
            m.new_thread()
            new_thread = m.remember({"role": "user", "content": str(item)})
            brain.reason(persona, new_thread)

    processes.run_async(_run)


@ability("Search past conversation history. Items: [what you are looking for]", order=18)
async def seek_history(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Load the history briefing so the model can identify which past conversation to replay."""
    logger.info("Ability: seek_history", {"persona": persona.id, "thread": thread.id})
    from application.core import history
    content = await history.briefing(persona)
    return Prompt(role="user", content=f"History briefing:\n\n{content}")


@ability("Replay a specific past conversation. Items: [filename from the briefing]", order=19)
async def replay(persona: Persona, thread: Thread, items: list) -> Prompt | None:
    """Load a specific history file and return its contents as context."""
    logger.info("Ability: replay", {"persona": persona.id, "thread": thread.id})
    from application.core import history
    filename = str(items[0]) if items else ""
    if not filename:
        return None
    content = await history.load_conversation(persona, filename)
    return Prompt(role="user", content=f"Past conversation:\n\n{content}")
