"""PersonIdentifier — batch extract identity facts from archived conversations.

Guard: one or more information{type: archive_done} signals with processed_at=None.
Job:   read all pending history files, one LLM call to extract identity facts,
       update person identity file, mark signals as processed,
       produce information{type: person_done}.

prompt() → returns extraction query if pending archive_done signals exist.
run(data) → saves identity facts, marks signals, produces person_done.
"""

from application.core.brain.data import Signal
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger, datetimes


def prompt(memory: Memory, persona: Persona) -> tuple[str, str] | None:
    pending = _pending_archive_done(memory)
    if not pending:
        return None

    from application.core import paths
    file_contents = _read_history_files(pending, persona, paths)
    if not file_contents:
        return None

    existing = paths.read(paths.person_identity(persona.id)) or "(none)"

    logger.info("person_identifier: extracting", {
        "persona_id": persona.id,
        "files": len(file_contents),
    })

    return (
        f"Existing identity facts:\n{existing}\n\n"
        f"Recent conversations:\n\n{'---\n'.join(file_contents)}\n\n"
        "What new identity facts about the person can you confirm from these conversations? "
        "Return only facts not already listed. Return empty list if nothing new.\n"
        'Return JSON: {"facts": ["...", ...]}',
        "",
    )


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    pending = _pending_archive_done(memory)
    if not pending:
        return False

    from application.core import paths
    now = datetimes.now()

    if data is not None:
        facts = data.get("facts", []) if isinstance(data, dict) else []
        if facts:
            paths.append_as_string(paths.person_identity(persona.id), "\n".join(facts) + "\n")

    # Mark all pending archive_done signals as processed
    for s in pending:
        s.processed_at = now

    # Produce person_done to trigger TraitIdentifier
    person_done = Signal(role="information", data={"type": "person_done"})
    memory.add_node(person_done)

    logger.info("person_identifier: done", {
        "persona_id": persona.id,
        "facts": len(data.get("facts", [])) if isinstance(data, dict) else 0,
    })
    return True


def _pending_archive_done(memory: Memory) -> list[Signal]:
    return [
        s for s in memory.signals()
        if s.role == "information"
        and s.data.get("type") == "archive_done"
        and s.processed_at is None
    ]


def _read_history_files(signals: list[Signal], persona, paths) -> list[str]:
    contents = []
    for s in signals:
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
