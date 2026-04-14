"""Meaning — noting things to remember."""

from application.core import paths
from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"The person wants {persona.name} to note or remember something specific"


def prompt(persona: Persona) -> str:
    existing = paths.read(paths.notes(persona.id))
    return (
        "The person wants you to explicitly save something for later — a fact, "
        "a reference, a code, a configuration, anything they want you to remember.\n\n"
        f"## Current Notes\n\n{existing.strip() or '(no notes yet)'}\n\n"
        "## Tools\n\n"
        "### save_notes\n"
        "Rewrite the notes file with the updated content.\n\n"
        "Parameters:\n"
        "- `content` (string, required): The complete updated notes text.\n\n"
        "### say\n"
        "Send a message to the person.\n\n"
        "Parameters:\n"
        "- `text` (string, required): The message to send.\n\n"
        "## Response Format\n\n"
        "Merge the new note into the existing notes. Remove anything the person "
        "asks to remove. Keep everything else. Return the full updated text:\n"
        "```json\n"
        '{"tool": "save_notes", "content": "updated notes text here", '
        '"say": "Noted!"}\n'
        "```\n\n"
        "No special permissions are needed for noting."
    )
