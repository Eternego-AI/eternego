"""Consent — per-persona action permission records."""

import re

from application.platform import logger, filesystem
from application.core import paths
from application.core.data import Persona


def _permissions_path(persona: Persona):
    return paths.home(persona.id) / "permissions.md"


def _ensure(persona: Persona) -> None:
    path = _permissions_path(persona)
    if not path.exists():
        filesystem.write(path, "## Granted\n\n## Denied\n\n## Pending\n")


def check(persona: Persona, action: str) -> str | None:
    """Return 'granted', 'denied', or None if no record exists for this action."""
    logger.info("Checking consent", {"persona": persona.id, "action": action})
    _ensure(persona)
    content = filesystem.read(_permissions_path(persona))
    action_lower = action.lower()
    section = None
    for line in content.splitlines():
        if line.startswith("## Granted"):
            section = "granted"
        elif line.startswith("## Denied"):
            section = "denied"
        elif line.startswith("## Pending"):
            section = None
        elif line.startswith("- ") and section in ("granted", "denied"):
            if action_lower in line.lower():
                return section
    return None


def pending(persona: Persona) -> list[dict]:
    """Return all pending consent requests as {action, thread_id} dicts."""
    logger.info("Reading pending consent", {"persona": persona.id})
    _ensure(persona)
    content = filesystem.read(_permissions_path(persona))
    result = []
    in_pending = False
    for line in content.splitlines():
        if line.startswith("## Pending"):
            in_pending = True
        elif line.startswith("## "):
            in_pending = False
        elif in_pending and line.startswith("- "):
            match = re.match(r"- (.+?) \[thread:(.+?)]", line)
            if match:
                result.append({"action": match.group(1), "thread_id": match.group(2)})
    return result


def request(persona: Persona, action: str, thread_id: str) -> None:
    """Add a pending consent request for the given action and originating thread."""
    logger.info("Recording consent request", {"persona": persona.id, "action": action})
    _ensure(persona)
    content = filesystem.read(_permissions_path(persona))
    entry = f"- {action} [thread:{thread_id}]"
    lines = content.splitlines()
    final = []
    for line in lines:
        final.append(line)
        if line.strip() == "## Pending":
            final.append(entry)
    filesystem.write(_permissions_path(persona), "\n".join(final) + "\n")


def resolve(persona: Persona, action: str, decision: str, statement: str) -> str | None:
    """Move a pending request to granted or denied. Returns the original thread_id or None if not found."""
    logger.info("Resolving consent", {"persona": persona.id, "action": action, "decision": decision})
    _ensure(persona)
    content = filesystem.read(_permissions_path(persona))
    action_lower = action.lower()
    thread_id = None

    lines = content.splitlines()
    remaining = []
    in_pending = False
    for line in lines:
        if line.startswith("## Pending"):
            in_pending = True
            remaining.append(line)
        elif line.startswith("## "):
            in_pending = False
            remaining.append(line)
        elif in_pending and line.startswith("- ") and action_lower in line.lower():
            match = re.match(r"- (.+?) \[thread:(.+?)]", line)
            if match and not thread_id:
                thread_id = match.group(2)
        else:
            remaining.append(line)

    if not thread_id:
        return None

    section = "## Granted" if decision == "granted" else "## Denied"
    entry = f'- {action} [thread:{thread_id}] "{statement}"'
    final = []
    for line in remaining:
        final.append(line)
        if line.strip() == section:
            final.append(entry)

    filesystem.write(_permissions_path(persona), "\n".join(final) + "\n")
    return thread_id
