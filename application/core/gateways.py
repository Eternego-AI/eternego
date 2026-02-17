"""Gateways — persona-scoped channel lifecycle, process-lived."""

from application.core.data import Channel, Gateway, Persona


_active: dict[str, dict[str, Gateway]] = {}


def of(persona: Persona) -> "PersonaGateway":
    """Return the gateway handle for this persona."""
    return PersonaGateway(persona)


class PersonaGateway:
    """Handle for one persona's active channels. Use via gateways.of(persona)."""

    def __init__(self, persona: Persona):
        self._persona = persona

    def add(self, gateway: Gateway) -> None:
        """Register an active channel gateway."""
        _active.setdefault(self._persona.id, {})[gateway.channel.name] = gateway

    def close(self, channel: Channel) -> bool:
        """Close a single channel. Returns True if it was active."""
        gw = _active.get(self._persona.id, {}).pop(channel.name, None)
        if gw:
            gw.close()
            return True
        return False

    def close_all(self) -> bool:
        """Close all channels. Returns True if any were active."""
        persona_channels = _active.pop(self._persona.id, {})
        for gw in persona_channels.values():
            gw.close()
        return bool(persona_channels)

    def is_active(self) -> bool:
        """True if the persona has any active channels."""
        return bool(_active.get(self._persona.id))
