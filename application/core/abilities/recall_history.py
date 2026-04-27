"""Ability — recall_history."""

from application.core import paths
from application.core.abilities import ability
from application.platform import logger


@ability("Pull past conversations and media from a given day (YYYY-MM-DD).")
async def recall_history(persona, date: str = "") -> str:
    logger.debug("ability.recall_history", {"persona": persona, "date": date})
    if not date:
        raise ValueError("date is required")
    entries = paths.read_files_matching(persona.id, paths.history(persona.id), f"*{date}*")
    live = paths.read_jsonl(paths.conversation(persona.id))
    live_lines = [
        f"[{e.get('time', '')}] {e['role']}: {e['content']}"
        for e in live if date in e.get("time", "")
    ]
    if live_lines:
        entries.append("Today's conversation:\n" + "\n".join(live_lines))
    gallery = paths.read_jsonl(paths.gallery(persona.id))
    media_lines = [
        f"[{entry['time']}] Image: {entry['source']} — {entry['answer']}"
        for entry in gallery
        if date in entry.get("time", "")
    ]
    if media_lines:
        entries.append("Media from that date:\n" + "\n".join(media_lines))
    if not entries:
        return "no conversations found for that date"
    return "\n\n".join(entries)
