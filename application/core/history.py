"""History — long-term conversation history for a persona."""

from application.platform import logger, filesystem, crypto, datetimes
from application.core import local_model, paths
from application.core.data import Persona, Thread
from application.core.exceptions import HistoryError


async def entries(persona: Persona) -> list[str]:
    """Read the agent's conversation history names."""
    logger.info("Listing history", {"persona_id": persona.id})
    try:
        names = []
        history_dir = paths.history(persona.id)
        if history_dir.exists():
            for file in sorted(history_dir.glob("*")):
                names.append(file.stem)
        return names
    except OSError as e:
        raise HistoryError("Could not list history entries") from e


async def delete(persona: Persona, hash_part: str) -> None:
    """Remove a history file by its name hash."""
    logger.info("Deleting history entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        for file in paths.history(persona.id).glob("*"):
            if crypto.generate_unique_id(file.stem) == hash_part:
                filesystem.delete(file)
                return
        raise HistoryError("History entry not found or already removed")
    except OSError as e:
        raise HistoryError("Could not delete history entry") from e


async def review(persona: Persona) -> str:
    """Read the history briefing index."""
    logger.info("Reviewing history briefing", {"persona_id": persona.id})
    try:
        path = paths.history_briefing(persona.id)
        return filesystem.read(path) if path.exists() else "(no history yet)"
    except OSError as e:
        raise HistoryError("Could not read history briefing") from e


async def recall(persona: Persona, filename: str) -> str:
    """Load a history file by filename."""
    logger.info("Recalling history file", {"persona_id": persona.id, "filename": filename})
    try:
        path = paths.history(persona.id) / filename
        if not path.exists():
            raise HistoryError(f"History file not found: {filename}")
        return filesystem.read(path)
    except OSError as e:
        raise HistoryError("Could not recall history file") from e


def save(persona: Persona, datetime, thread: Thread, event: str, details: str) -> str:
    """Write a history entry and return the filename. Event must be conversation, schedule, or remind."""
    stamp = datetimes.date_stamp(datetime)
    prefix = "" if thread.public else "."
    filename = f"{prefix}{event}-{stamp}-{thread.id[:8]}.md"
    filesystem.write(paths.history(persona.id) / filename, details)
    return filename


def brief(persona: Persona, title: str, summary: str, filename: str) -> None:
    """Append an entry to the briefing index."""
    briefing_path = paths.history_briefing(persona.id)
    row = f"| {title} | {summary} | {filename} |\n"
    if not briefing_path.exists():
        filesystem.write(briefing_path, "| Title | Summary | File |\n|-------|---------|------|\n" + row)
    else:
        filesystem.append(briefing_path, row)


async def summarize_conversation(persona: Persona, thread: Thread) -> None:
    """Summarize a finished thread, write it to disk, and append to the briefing if public."""
    logger.info("Summarizing conversation to history", {"persona_id": persona.id, "thread": thread.id})
    from application.core import memories
    messages = memories.agent(persona).as_messages(thread.id)
    if not messages:
        return
    try:
        summary = await local_model.summarize_thread(persona.model.name, messages)
        title = summary["title"]
        summary_text = summary["summary"]

        lines = [f"# {title}\n"]
        for msg in messages:
            if msg.get("content"):
                lines.append(f"**{msg['role'].capitalize()}:** {msg['content']}\n")

        filename = save(persona, datetimes.now(), thread, "conversation", "\n".join(lines))

        if thread.public:
            brief(persona, title, summary_text, filename)

    except OSError as e:
        raise HistoryError("Could not save conversation to history") from e
