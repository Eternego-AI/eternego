"""Destiny abilities — scheduling events and reminders."""

from application.platform import logger
from application.core.data import Channel, Persona, Prompt, Thread
from application.core.brain.abilities._base import ability


@ability(
"Schedule an event at a specific datetime. Items: [{trigger: 'YYYY-MM-DD HH:MM', content: 'description'}]",
["commander", "conversational", "secretary"],
order=15)
async def schedule(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Save each scheduled event to disk. Returns feedback so the model can confirm or report errors."""
    logger.info("Ability: schedule", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from datetime import datetime
    from application.core import paths
    parts = []
    for item in items:
        if not isinstance(item, dict):
            parts.append("Invalid item — expected an object with trigger and content.")
            continue
        trigger = str(item.get("trigger", "")).strip()
        content = str(item.get("content", "")).strip()
        if not trigger:
            parts.append("Missing trigger — use clarify to ask the person when this should happen.")
            continue
        try:
            datetime.strptime(trigger, "%Y-%m-%d %H:%M")
        except ValueError:
            parts.append(f"Invalid trigger format '{trigger}' — must be YYYY-MM-DD HH:MM.")
            continue
        if not content:
            parts.append("Missing content — use clarify to ask the person what this event is about.")
            continue
        await paths.save_destiny_entry(persona.id, "schedule", trigger, thread.id, content)
        parts.append(f"Scheduled: {trigger} — {content}")
    return Prompt(role="user", content="\n".join(parts) if parts else "No items were scheduled.")


@ability(
"Set a reminder at a specific datetime. Items: [{trigger: 'YYYY-MM-DD HH:MM', content: 'description'}]",
["commander", "conversational", "secretary"],
order=16)
async def remind(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Save each reminder to disk. Returns feedback so the model can confirm or report errors."""
    logger.info("Ability: remind", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from datetime import datetime
    from application.core import paths
    parts = []
    for item in items:
        if not isinstance(item, dict):
            parts.append("Invalid item — expected an object with trigger and content.")
            continue
        trigger = str(item.get("trigger", "")).strip()
        content = str(item.get("content", "")).strip()
        if not trigger:
            parts.append("Missing trigger — use clarify to ask the person when this should happen.")
            continue
        try:
            datetime.strptime(trigger, "%Y-%m-%d %H:%M")
        except ValueError:
            parts.append(f"Invalid trigger format '{trigger}' — must be YYYY-MM-DD HH:MM.")
            continue
        if not content:
            parts.append("Missing content — use clarify to ask the person what you want to be reminded about.")
            continue
        await paths.save_destiny_entry(persona.id, "reminder", trigger, thread.id, content)
        parts.append(f"Reminder set: {trigger} — {content}")
    return Prompt(role="user", content="\n".join(parts) if parts else "No reminders were set.")


@ability(
"Get scheduled events. Items: []",
["commander", "conversational", "secretary"],
order=20)
async def calendar(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Read pending scheduled events and return them for the model to reason about."""
    logger.info("Ability: calendar", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from application.core import paths
    entries = await paths.read_files_matching(persona.id, await paths.destiny(persona.id), "schedule-*.md")
    if not entries:
        return Prompt(role="user", content="No scheduled events found.")
    return Prompt(role="user", content="Scheduled events:\n" + "\n---\n".join(entries))


@ability(
"Get reminders. Items: []",
["commander", "conversational", "secretary"],
order=21)
async def reminder(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Read pending reminders and return them for the model to reason about."""
    logger.info("Ability: reminder", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from application.core import paths
    entries = await paths.read_files_matching(persona.id, await paths.destiny(persona.id), "reminder-*.md")
    if not entries:
        return Prompt(role="user", content="No reminders found.")
    return Prompt(role="user", content="Reminders:\n" + "\n---\n".join(entries))


@ability(
"Manifest a destiny entry into history — mark it as done. Items: [filename from calendar or reminder]",
["secretary", "commander", "conversational"],
order=27)
async def manifest_destiny(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Read the destiny entry, write to history, and delete it."""
    logger.info("Ability: manifest_destiny", {"persona": persona.id, "thread": thread.id, "channel": channel.name})
    from application.core import paths
    from application.platform import filesystem
    parts = []
    destiny_dir = await paths.destiny(persona.id)
    for filename in items:
        path = destiny_dir / str(filename)
        content = await paths.read(path)
        if not content:
            parts.append(f"Entry not found: {filename}")
            continue
        await paths.add_history_entry(persona.id, "destiny", content)
        filesystem.delete(path)
        parts.append(f"Manifested: {filename}")
    return Prompt(role="user", content="\n".join(parts) if parts else "Nothing to manifest.")
