"""TraitIdentifier — batch extract traits from archived conversations.

Guard: one or more information{type: person_done} signals with processed_at=None.
Job:   find correlated archive_done signals, read history files,
       one LLM call to extract traits, update traits file,
       mark person_done signals as processed, produce trait_done.

prompt() → returns extraction query if pending person_done signals exist.
run(data) → saves traits, marks signals, produces trait_done.
"""

from application.core.brain.data import Signal
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger, datetimes


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    pending = _pending_person_done(memory)
    if not pending:
        return None

    from application.core import paths
    # Read from already-processed archive_done signals (processed_at is set)
    archive_files = _read_all_recent_files(memory, persona, paths)
    if not archive_files:
        return None

    existing = paths.read(paths.person_traits(persona.id)) or "(none)"

    logger.info("trait_identifier: extracting", {
        "persona_id": persona.id,
        "files": len(archive_files),
    })

    return (
        f"Existing traits and preferences:\n{existing}\n\n"
        f"Recent conversations:\n\n{'---\n'.join(archive_files)}\n\n"
        "What new preferences, habits, or behavioral traits about the person can you confirm? "
        "Return only traits not already listed. Return empty list if nothing new.\n"
        'Return JSON: {"traits": ["...", ...]}',
        "",
    )


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    pending = _pending_person_done(memory)
    if not pending:
        return False

    from application.core import paths
    now = datetimes.now()

    if data is not None:
        traits = data.get("traits", []) if isinstance(data, dict) else []
        if traits:
            paths.add_person_traits(persona.id, "\n".join(traits) + "\n")

    for s in pending:
        s.processed_at = now

    trait_done = Signal(role="information", data={"type": "trait_done"})
    memory.add_node(trait_done)

    logger.info("trait_identifier: done", {
        "persona_id": persona.id,
        "traits": len(data.get("traits", [])) if isinstance(data, dict) else 0,
    })
    return True


def _pending_person_done(memory: Memory) -> list[Signal]:
    return [
        s for s in memory.signals()
        if s.role == "information"
        and s.data.get("type") == "person_done"
        and s.processed_at is None
    ]


def _read_all_recent_files(memory: Memory, persona, paths) -> list[str]:
    """Read history files from processed archive_done signals."""
    contents = []
    for s in memory.signals():
        if s.role == "information" and s.data.get("type") == "archive_done" and s.processed_at is not None:
            filename = s.data.get("filename", "")
            if not filename:
                continue
            try:
                content = paths.read(paths.history(persona.id) / filename)
                if content:
                    contents.append(content)
            except Exception:
                pass
    return contents
