"""StruggleIdentifier — batch extract struggles from archived conversations.

Guard: one or more information{type: wish_done} signals with processed_at=None.

prompt() → returns extraction query if pending wish_done signals exist.
run(data) → saves struggles, marks signals as processed (cleans up information chain).
"""

from application.core.brain.data import Signal
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger, datetimes


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    pending = _pending_wish_done(memory)
    if not pending:
        return None

    from application.core import paths
    archive_files = _read_all_recent_files(memory, persona, paths)
    if not archive_files:
        return None

    existing = paths.read(paths.struggles(persona.id)) or "(none)"

    logger.info("struggle_identifier: extracting", {"persona_id": persona.id})

    return (
        f"Existing struggles and challenges:\n{existing}\n\n"
        f"Recent conversations:\n\n{'---\n'.join(archive_files)}\n\n"
        "What new struggles, frustrations, or challenges has the person expressed? "
        "Return only struggles not already listed. Return empty list if nothing new.\n"
        'Return JSON: {"struggles": ["...", ...]}',
        "",
    )


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    pending = _pending_wish_done(memory)
    if not pending:
        return False

    from application.core import paths
    now = datetimes.now()

    if data is not None:
        struggles = data.get("struggles", []) if isinstance(data, dict) else []
        if struggles:
            paths.add_struggles(persona.id, "\n".join(struggles) + "\n")

    for s in pending:
        s.processed_at = now

    # Clean up the processed information signals from memory
    # (archive_done → person_done → trait_done → wish_done are all processed)
    _cleanup_info_chain(memory, now)

    logger.info("struggle_identifier: done", {"persona_id": persona.id})
    return True


def _pending_wish_done(memory: Memory) -> list[Signal]:
    return [
        s for s in memory.signals()
        if s.role == "information"
        and s.data.get("type") == "wish_done"
        and s.processed_at is None
    ]


def _read_all_recent_files(memory: Memory, persona, paths) -> list[str]:
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


def _cleanup_info_chain(memory: Memory, now) -> None:
    """Remove fully-processed information signals from memory."""
    chain_types = {"archive_done", "person_done", "trait_done", "wish_done"}
    to_remove = [
        s.id for s in memory.signals()
        if s.role == "information"
        and s.data.get("type") in chain_types
        and s.processed_at is not None
    ]
    for sid in to_remove:
        memory.remove_node(sid)
