"""Meaning — noting things to remember."""

from application.core import paths
from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"The person wants {persona.name} to note or remember something specific"


def prompt(persona: Persona) -> str:
    existing = paths.read(paths.notes(persona.id))
    return (
        "The person has asked you to hold something for them — a fact, a reference, a code, a "
        "configuration, anything they want you to remember. What you save here is what you will "
        "be handed back on future ticks under *What You've Been Asked to Remember*, so write it "
        "in a shape that will still make sense to you later.\n\n"
        f"## What They've Already Asked You to Hold\n\n{existing.strip() or '(nothing yet)'}\n\n"
        "## Tools\n\n"
        "- `save_notes(content)` — REPLACES the whole notes file. `content` must contain every "
        "line above byte-for-byte, plus the new note appended. Only drop a line if the person "
        "explicitly asked to remove that item. Never reword or reorder the existing lines.\n"
        "- `say(text)` — message the person.\n\n"
        "## Output\n\n"
        "```json\n"
        '{"reason": "<what is being added or removed>",\n'
        ' "tool": "save_notes",\n'
        ' "content": "<old notes verbatim + new note>",\n'
        ' "say": "<short confirmation>"}\n'
        "```"
    )
