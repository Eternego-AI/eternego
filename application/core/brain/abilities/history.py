"""History abilities — searching, replaying, and archiving past conversations."""

from application.platform import logger
from application.core import paths
from application.core.data import Channel, Persona, Prompt, Thread
from application.core.brain.abilities._base import ability


@ability(
"Search past conversation history. Items: [what you are looking for]",
["commander", "conversational"],
order=18)
async def seek_history(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Load the history briefing so the model can identify which past conversation to replay."""
    logger.info("Ability: seek_history", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    content = await paths.read_history_brief(persona.id, "(no history yet)")
    return Prompt(role="user", content=f"History briefing:\n\n{content}")


@ability(
"Replay a specific past conversation. Items: [filename from the briefing]",
["commander", "conversational"],
order=19)
async def replay(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Load a specific history file and return its contents as context."""
    logger.info("Ability: replay", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    filename = str(items[0]) if items else ""
    if not filename:
        return None
    content = await paths.read(await paths.history(persona.id) / filename)
    return Prompt(role="user", content=f"Past conversation:\n\n{content}")


@ability(
"Archive this conversation to long-term history. Items: [{title: 'short title', summary: 'one-line summary', content: 'full markdown body'}]",
["reflective"],
order=22)
async def archive(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Write a conversation summary to history and append it to the briefing index."""
    logger.info("Ability: archive", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from application.platform import datetimes
    parts = []
    for item in items:
        if not isinstance(item, dict):
            parts.append("Invalid item — expected an object with title, summary, and content.")
            continue
        title = str(item.get("title", "conversation")).strip()
        summary = str(item.get("summary", "")).strip()
        content = str(item.get("content", "")).strip()
        if not content:
            parts.append("Missing content — nothing was archived.")
            continue
        stamp = datetimes.date_stamp(datetimes.now())
        prefix = "" if thread.public else "."
        filename = f"{prefix}conversation-{stamp}-{thread.id[:8]}.md"
        await paths.save_as_string(await paths.history(persona.id) / filename, content)
        if thread.public:
            await paths.add_history_briefing(
                persona.id,
                "| Title | Summary | File |\n|-------|---------|------|",
                f"| {title} | {summary} | {filename} |\n"
            )
        parts.append(f"Archived: {filename}")
    return Prompt(role="user", content="\n".join(parts) if parts else "Nothing was archived.")
