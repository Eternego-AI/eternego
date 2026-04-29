"""Ability — check_health."""

from application.core import paths
from application.core.abilities import ability
from application.platform import logger


@ability("Read the last health-check entries the body logged — fault counts and which "
         "providers failed in recent ticks. Use when troubleshooting to see whether the "
         "machine itself has been struggling. count: how many recent entries (default 5).")
async def check_health(persona, count: int = 5) -> str:
    logger.debug("ability.check_health", {"persona": persona, "count": count})
    if count < 1:
        count = 5
    entries = paths.read_jsonl(paths.health_log(persona.id))[-count:]
    if not entries:
        return "(no health checks logged yet)"
    lines = []
    for entry in entries:
        when = entry.get("time", "?")
        loop = entry.get("loop_number", "?")
        faults = entry.get("fault_count", 0)
        providers = ", ".join(entry.get("fault_providers", [])) or "none"
        lines.append(f"- {when} (loop {loop}) — {faults} fault(s); providers: {providers}")
    return "\n".join(lines)
