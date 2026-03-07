"""Registry — in-process store for running personas and their minds."""

from typing import TYPE_CHECKING

from datetime import timedelta

from application.platform import datetimes
from application.core.exceptions import RegistryError

if TYPE_CHECKING:
    from application.core.brain.mind import Mind
    from application.core.data import Persona

_minds: dict[str, "Mind"] = {}
_personas: dict[str, "Persona"] = {}
_pairing_codes: dict[str, dict] = {}  # code → {persona_id, channel_name, created_at}


def save(persona: "Persona", mind: "Mind") -> None:
    """Register a running persona and its mind."""
    _personas[persona.id] = persona
    _minds[persona.id] = mind


def mind(persona_id: str) -> "Mind | None":
    """Return the running Mind for a persona, or None if not started."""
    return _minds.get(persona_id)


def get_persona(persona_id: str) -> "Persona | None":
    """Return the running Persona, or None if not started."""
    return _personas.get(persona_id)


def remove(persona_id: str) -> None:
    """Remove a persona and its mind from the registry."""
    _minds.pop(persona_id, None)
    _personas.pop(persona_id, None)


def all() -> list["Persona"]:
    """Return all currently running personas."""
    return list(_personas.values())


def pair(persona: "Persona", channel: "Channel") -> str:
    """Generate a pairing code, store it in-memory, and return it."""
    import secrets
    code = secrets.token_hex(3).upper()
    _pairing_codes[code] = {
        "persona_id": persona.id,
        "channel_type": channel.type,
        "channel_name": channel.name,
        "created_at": datetimes.now(),
    }
    return code


def take_code(code: str) -> tuple["Persona", str, str]:
    """Claim a pairing code and return (persona, channel_type, channel_name).

    Raises RegistryError if the code is invalid or expired.
    Removes the code from the store on success.
    """
    entry = _pairing_codes.get(code.upper())
    if not entry:
        raise RegistryError("Pairing code is invalid or has expired.")
    if datetimes.now() - entry["created_at"] > timedelta(minutes=10):
        _pairing_codes.pop(code.upper(), None)
        raise RegistryError("Pairing code has expired. Ask the persona to send a new message to get a fresh code.")
    persona = _personas.get(entry["persona_id"])
    if not persona:
        _pairing_codes.pop(code.upper(), None)
        raise RegistryError("The persona associated with this pairing code could not be found.")
    _pairing_codes.pop(code.upper(), None)
    return persona, entry["channel_type"], entry["channel_name"]
