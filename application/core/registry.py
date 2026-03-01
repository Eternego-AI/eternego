"""Registry — in-process store for running personas and their minds."""

from typing import TYPE_CHECKING

from application.platform import datetimes

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


def get_mind(persona_id: str) -> "Mind | None":
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


def save_pairing_code(code: str, persona_id: str, channel_type: str, channel_name: str) -> None:
    """Store a pairing code in-memory for the current session."""
    _pairing_codes[code.upper()] = {
        "persona_id": persona_id,
        "channel_type": channel_type,
        "channel_name": channel_name,
        "created_at": datetimes.now(),
    }


def get_pairing_code(code: str) -> dict | None:
    """Return the pairing code entry, or None if not found."""
    return _pairing_codes.get(code.upper())


def remove_pairing_code(code: str) -> None:
    """Remove a pairing code from the in-memory store."""
    _pairing_codes.pop(code.upper(), None)
