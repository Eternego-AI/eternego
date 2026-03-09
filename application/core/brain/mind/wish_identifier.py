"""WishIdentifier — batch extract wishes from archived conversations.

Guard: one or more information{type: trait_done} signals with processed_at=None.

prompt() → returns extraction query if pending trait_done signals exist.
run(data) → saves wishes, marks signals, produces wish_done.
"""

from application.core.brain.data import Signal
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger, datetimes


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    pending = _pending_trait_done(memory)
    if not pending:
        return None

    from application.core import paths
    archive_files = _read_all_recent_files(memory, persona, paths)
    if not archive_files:
        return None

    existing = paths.read(paths.wishes(persona.id)) or "(none)"

    logger.info("wish_identifier: extracting", {"persona_id": persona.id})

    return (
        f"Existing wishes and aspirations:\n{existing}\n\n"
        f"Recent conversations:\n\n{'---\n'.join(archive_files)}\n\n"
        "What new wishes, goals, or aspirations has the person expressed? "
        "Return only wishes not already listed. Return empty list if nothing new.\n"
        'Return JSON: {"wishes": ["...", ...]}',
        "",
    )


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    pending = _pending_trait_done(memory)
    if not pending:
        return False

    from application.core import paths
    now = datetimes.now()

    if data is not None:
        wishes = data.get("wishes", []) if isinstance(data, dict) else []
        if wishes:
            paths.append_as_string(paths.wishes(persona.id), "\n".join(wishes) + "\n")

    for s in pending:
        s.processed_at = now

    wish_done = Signal(role="information", data={"type": "wish_done"})
    memory.add_node(wish_done)

    logger.info("wish_identifier: done", {"persona_id": persona.id})
    return True


def _pending_trait_done(memory: Memory) -> list[Signal]:
    return [
        s for s in memory.signals()
        if s.role == "information"
        and s.data.get("type") == "trait_done"
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
