"""Values — builds the system prompt that defines who the persona is and what it can do."""

from application.platform import filesystem, reflections
from application.core.brain import abilities
from application.core.brain import consent
from application.core.brain import cornerstone
from application.core.brain.skills import being_persona as being_persona_skill
from application.core.data import Channel, Persona


def build(persona: Persona, channel: Channel) -> str:
    """Compose the full system prompt from cornerstone, abilities, identity, and pending permissions."""
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

    persona_context = _read(persona.storage_dir / "persona-context.md")
    person_identity = _read(persona.storage_dir / "person-identity.md")
    being_persona = being_persona_skill.skill(persona)

    sections = [cornerstone.instruction(persona), f"## Abilities\n\n{abilities_doc}"]

    if being_persona:
        sections.append(being_persona)

    if persona_context:
        sections.append(f"# Persona Context\n\n{persona_context}")
    if person_identity:
        sections.append(f"# Person Identity\n\n{person_identity}")

    pending = consent.pending(persona)
    if pending:
        pending_lines = "\n".join(f"- {p['action']} (thread: {p['thread_id']})" for p in pending)
        sections.append(
            f"# Pending Permissions\n\n"
            f"The following permission requests are awaiting a response from the person:\n\n{pending_lines}\n\n"
            f"If the person's message is responding to one of these, use resolve_permission to record their decision and resume the waiting thread."
        )

    return "\n\n".join(sections)
