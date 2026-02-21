"""Brain — the persona's cognitive processing core."""

from application.platform import logger, strings, processes, reflections, filesystem
from application.platform.observer import Command
from application.core import abilities, bus, history, local_model, memories, permissions
from application.core.data import Channel, Persona, Prompt, Thread

_BASE = "You are a persona. Use the abilities below to respond. Return ONLY valid JSON — each key is an ability name, the value is a list. Return {} when done."


def _system(persona: Persona, channel: Channel) -> str:
    abilities_doc = "\n".join(
        f'- "{name}": {fn.ability}'
        for name, fn in reflections.sorted_by(abilities, "ability")
        if channel.authority in fn.ability_scopes
    )

    def _read(path) -> str:
        try:
            return filesystem.read(path).strip()
        except OSError:
            return ""

    persona_identity = _read(persona.storage_dir / "persona-identity.md")
    persona_context = _read(persona.storage_dir / "persona-context.md")
    person_identity = _read(persona.storage_dir / "person-identity.md")
    being_persona = _read(persona.storage_dir / "skills" / "being-persona.md")

    sections = [_BASE, f"## Abilities\n\n{abilities_doc}"]

    if being_persona:
        sections.append(being_persona)

    if persona_identity or persona_context:
        sections.append(f"# Persona Identity\n\n{'\n'.join(filter(None, [persona_identity, persona_context]))}")
    if person_identity:
        sections.append(f"# Person Identity\n\n{person_identity}")

    pending = permissions.pending(persona)
    if pending:
        pending_lines = "\n".join(f"- {p['action']} (thread: {p['thread_id']})" for p in pending)
        sections.append(
            f"# Pending Permissions\n\n"
            f"The following permission requests are awaiting a response from the person:\n\n{pending_lines}\n\n"
            f"If the person's message is responding to one of these, use resolve_permission to record their decision and resume the waiting thread."
        )

    return "\n\n".join(sections)


def reason(persona: Persona, thread: Thread, channel: Channel) -> None:
    """Schedule reasoning as a background task — never blocks the caller."""
    logger.info("Brain reasoning", {"persona": persona.id, "thread": thread.id})
    messages = [{"role": "system", "content": _system(persona, channel)}]
    messages += memories.agent(persona).as_messages(thread.id)

    async def _run():
        await bus.propose("Thinking", {"persona": persona, "thread": thread})
        loops = await _reason(persona, thread, channel, messages)
        await bus.broadcast("Thought Concluded", {"persona": persona, "thread": thread, "loops": loops})
        await history.persist(persona, thread)

    processes.run_async(_run)


async def _reason(persona: Persona, thread: Thread, channel: Channel, messages: list[dict]) -> int:
    loop = 0
    while True:
        responses = await bus.ask("Reasoning Thought", {"persona": persona, "thread": thread, "loop": loop})
        if any(isinstance(r, Command) and r.title == "Stop Reasoning" for r in responses):
            break

        plan_title = "Reasoning" if loop == 0 else "Chaining"
        responses = await bus.propose(plan_title, {"persona": persona, "thread": thread, "channel": channel, "loop": loop})
        if any(isinstance(r, Command) and r.title == "Stop Reasoning" for r in responses):
            break

        response = await local_model.respond(persona.model.name, messages, json_mode=True)
        parsed = strings.to_json(response)
        if parsed is None:
            parsed = {"say": [response]}
        messages.append({"role": "assistant", "content": response})
        loop += 1

        if not parsed:
            if loop == 1:
                messages.append({"role": "user", "content": "You must respond to the person. Use the say ability to send them a message."})
                continue
            break

        new_prompts = []
        for key, value in parsed.items():
            if not value or not reflections.has_ability(abilities, key, "ability"):
                continue
            value = value if isinstance(value, list) else [value]
            fn = getattr(abilities, key)
            if channel.authority not in fn.ability_scopes:
                new_prompts.append(Prompt(role="user", content=f"{key} is not available on this channel."))
                continue
            try:
                result = await fn(persona, thread, channel, value)
                if result:
                    new_prompts.append(result)
            except Exception as e:
                logger.warning("Ability failed", {"ability": key, "error": str(e)})
                new_prompts.append(Prompt(role="user", content=f"{key} failed: {e}"))

        if not new_prompts:
            break

        for p in new_prompts:
            messages.append({"role": p.role, "content": p.content})

    return loop
