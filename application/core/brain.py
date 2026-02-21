"""Brain — the persona's cognitive processing core."""

from application.platform import logger, strings, processes, reflections, filesystem
from application.core import abilities, history, local_model, memories, permissions
from application.core.data import Persona, Prompt, Thread

_BASE = "You are a persona. Use the abilities below to respond. Return ONLY valid JSON — each key is an ability name, the value is a list. Return {} when done."


def _system(persona: Persona) -> str:
    abilities_doc = "\n".join(
        f'- "{name}": {fn.ability}'
        for name, fn in reflections.sorted_by(abilities, "ability")
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


def reason(persona: Persona, thread: Thread) -> None:
    """Schedule reasoning as a background task — never blocks the caller."""
    logger.info("Brain reasoning", {"persona": persona.id, "thread": thread.id})
    messages = [{"role": "system", "content": _system(persona)}]
    messages += memories.agent(persona).as_messages(thread.id)

    async def _run():
        await _reason(persona, thread, messages)
        await history.persist(persona, thread)

    processes.run_async(_run)


async def _reason(persona: Persona, thread: Thread, messages: list[dict]) -> None:
    while True:
        response = await local_model.respond(persona.model.name, messages)
        parsed = strings.to_json(response)
        messages.append({"role": "assistant", "content": response})

        new_prompts = []
        for key, value in parsed.items():
            if not value or not reflections.has_ability(abilities, key, "ability"):
                continue
            fn = getattr(abilities, key)
            try:
                result = await fn(persona, thread, value)
                if result:
                    new_prompts.append(result)
            except Exception as e:
                logger.warning("Ability failed", {"ability": key, "error": str(e)})
                new_prompts.append(Prompt(role="user", content=f"{key} failed: {e}"))

        if not new_prompts:
            break

        for p in new_prompts:
            messages.append({"role": p.role, "content": p.content})
