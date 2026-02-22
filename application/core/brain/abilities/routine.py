"""Routine abilities — listing, adding, and removing recurring scheduled specs."""

from application.platform import logger, filesystem
from application.core import paths
from application.core.data import Channel, Persona, Prompt, Thread
from application.core.brain.abilities._base import ability


@ability(
"List all configured routines. Items: []",
["commander", "conversational"],
order=23)
async def list_routines(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Return all routines currently scheduled for this persona."""
    logger.info("Ability: list_routines", {"persona": persona.id, "thread": thread.id})
    path = await paths.routines(persona.id)
    data = filesystem.read_json(path) if path.exists() else {"routines": []}
    if not data["routines"]:
        return Prompt(role="user", content="No routines configured.")
    rows = "\n".join(f"- {r['spec']} at {r['time']} ({r['recurrence']})" for r in data["routines"])
    return Prompt(role="user", content=f"Routines:\n{rows}")


@ability(
"Add a recurring routine. Items: [{spec: 'sleep|diary', time: 'HH:MM', recurrence: 'daily'}]",
["commander", "conversational"],
order=24)
async def add_routine(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Add a new routine entry to the persona's routines file."""
    logger.info("Ability: add_routine", {"persona": persona.id, "thread": thread.id})
    parts = []
    for item in items:
        if not isinstance(item, dict):
            parts.append("Invalid item — expected an object with spec, time, and recurrence.")
            continue
        spec = str(item.get("spec", "")).strip()
        time = str(item.get("time", "")).strip()
        recurrence = str(item.get("recurrence", "daily")).strip()
        if not spec or not time:
            parts.append("Missing spec or time — cannot add routine.")
            continue
        await paths.add_routine(persona.id, spec, time, recurrence)
        parts.append(f"Routine added: {spec} at {time} ({recurrence})")
    return Prompt(role="user", content="\n".join(parts) if parts else "No routines added.")


@ability(
"Remove a routine by spec name. Items: [spec name]",
["commander", "conversational"],
order=25)
async def remove_routine(persona: Persona, thread: Thread, channel: Channel, items: list) -> Prompt | None:
    """Remove a routine entry from the persona's routines file."""
    logger.info("Ability: remove_routine", {"persona": persona.id, "thread": thread.id})
    path = await paths.routines(persona.id)
    data = filesystem.read_json(path) if path.exists() else {"routines": []}
    parts = []
    for spec in items:
        spec = str(spec).strip()
        before = len(data["routines"])
        data["routines"] = [r for r in data["routines"] if r["spec"] != spec]
        if len(data["routines"]) < before:
            parts.append(f"Routine removed: {spec}")
        else:
            parts.append(f"Routine not found: {spec}")
    filesystem.write_json(path, data)
    return Prompt(role="user", content="\n".join(parts) if parts else "No routines removed.")
