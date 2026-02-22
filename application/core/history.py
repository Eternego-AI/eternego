"""History — long-term conversation history for a persona."""

import time

from application.platform import logger, filesystem, crypto, datetimes
from application.core import local_model
from application.core.data import Persona, Thread
from application.core.exceptions import IdentityError


async def start(persona: Persona) -> None:
    """Create the history directory for a new persona."""
    logger.info("Starting history", {"persona_id": persona.id})
    try:
        filesystem.ensure_dir(persona.storage_dir / "history")
    except OSError as e:
        raise IdentityError("Failed to start history") from e


async def entries(persona: Persona) -> list[str]:
    """Read the agent's conversation history names."""
    logger.info("Reading history entries", {"persona_id": persona.id})
    try:
        names = []
        history_dir = persona.storage_dir / "history"
        if history_dir.exists():
            for file in sorted(history_dir.glob("*")):
                names.append(file.stem)
        return names
    except OSError as e:
        raise IdentityError("Failed to read history entries") from e


async def delete(persona: Persona, hash_part: str) -> None:
    """Remove a conversation file from history by its name hash."""
    logger.info("Deleting history entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        history_dir = persona.storage_dir / "history"
        for file in history_dir.glob("*"):
            if crypto.generate_unique_id(file.stem) == hash_part:
                filesystem.delete(file)
                return
        raise IdentityError("History entry not found or already removed")
    except OSError as e:
        raise IdentityError("Failed to delete history entry") from e


async def persist(persona: Persona, thread: Thread) -> None:
    """Summarize a finished thread, write it to disk, and append to the briefing if public."""
    logger.info("Persisting thread to history", {"persona_id": persona.id, "thread": thread.id})
    from application.core import memories
    messages = memories.agent(persona).as_messages(thread.id)
    if not messages:
        return
    try:
        summary = await local_model.summarize_thread(persona.model.name, messages)
        title = summary["title"]
        summary_text = summary["summary"]

        stamp = datetimes.date_stamp(datetimes.now())
        prefix = "" if thread.public else "."
        filename = f"{prefix}{stamp}-{thread.id[:8]}.md"
        history_dir = persona.storage_dir / "history"

        lines = [f"# {title}\n"]
        for msg in messages:
            if msg.get("content"):
                lines.append(f"**{msg['role'].capitalize()}:** {msg['content']}\n")
        filesystem.write(history_dir / filename, "\n".join(lines))

        if thread.public:
            briefing_path = history_dir / "briefing.md"
            row = f"| {title} | {summary_text} | {filename} |\n"
            if not briefing_path.exists():
                filesystem.write(briefing_path, "| Title | Summary | File |\n|-------|---------|------|\n" + row)
            else:
                filesystem.append(briefing_path, row)

    except OSError as e:
        raise IdentityError("Failed to persist thread to history") from e


async def briefing(persona: Persona) -> str:
    """Read the history briefing index."""
    logger.info("Reading history briefing", {"persona_id": persona.id})
    try:
        path = persona.storage_dir / "history" / "briefing.md"
        return filesystem.read(path) if path.exists() else "(no history yet)"
    except OSError as e:
        raise IdentityError("Failed to read history briefing") from e


async def record_event(persona: Persona, title: str, content: str) -> None:
    """Write a fired destiny event into history."""
    logger.info("Recording event in history", {"persona_id": persona.id, "title": title})
    try:
        stamp = datetimes.stamp(datetimes.now())
        filename = f"{datetimes.date_stamp(datetimes.now())}-event-{stamp}.md"
        history_dir = persona.storage_dir / "history"
        filesystem.write(history_dir / filename, f"# {title}\n\n{content}\n")
    except OSError as e:
        raise IdentityError("Failed to record event in history") from e


async def load_conversation(persona: Persona, filename: str) -> str:
    """Load a specific history conversation file by filename."""
    logger.info("Loading history conversation", {"persona_id": persona.id, "filename": filename})
    try:
        path = persona.storage_dir / "history" / filename
        if not path.exists():
            raise IdentityError(f"History file not found: {filename}")
        return filesystem.read(path)
    except OSError as e:
        raise IdentityError("Failed to load history conversation") from e



