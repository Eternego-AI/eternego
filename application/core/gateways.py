"""Gateways — persona-scoped conversation channel registry, process-lived."""

from application.core.data import Channel, Gateway, Persona


_active: dict[str, dict[str, Gateway]] = {}  # persona_id → {channel_key → Gateway}


def _key(channel: Channel) -> str:
    return f"{channel.type}:{channel.name}"


def of(persona: Persona) -> "PersonaGateway":
    """Return the gateway handle for this persona."""
    return PersonaGateway(persona)


class PersonaGateway:
    """Handle for one persona's active gateways. Use via gateways.of(persona)."""

    def __init__(self, persona: Persona):
        self._persona = persona

    def add(self, gateway: Gateway) -> None:
        """Register a gateway."""
        _active.setdefault(self._persona.id, {})[_key(gateway.channel)] = gateway

    def find(self, channel: Channel) -> Gateway | None:
        """Return the gateway for the given channel, or None."""
        return _active.get(self._persona.id, {}).get(_key(channel))

    def all(self) -> list[Gateway]:
        """Return all active gateways for this persona."""
        return list(_active.get(self._persona.id, {}).values())

    def close(self, channel: Channel) -> bool:
        """Remove a single gateway. Returns True if it was active."""
        gw = _active.get(self._persona.id, {}).pop(_key(channel), None)
        return gw is not None

    def close_all(self) -> bool:
        """Remove all gateways. Returns True if any were active."""
        persona_gws = _active.pop(self._persona.id, {})
        return bool(persona_gws)

    def is_active(self) -> bool:
        """True if the persona has any active gateways."""
        return bool(_active.get(self._persona.id))
