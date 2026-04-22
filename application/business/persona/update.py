"""Persona — change vital state or models in place."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Model, Persona
from application.core.exceptions import IdentityError


_ALLOWED_STATUS = {"active", "sick", "hibernate"}


@dataclass
class UpdateData:
    persona: Persona


async def update(
    persona: Persona,
    status: str | None = None,
    thinking: Model | None = None,
    vision: Model | None = None,
    frontier: Model | None = None,
    clear_vision: bool = False,
    clear_frontier: bool = False,
) -> Outcome[UpdateData]:
    """Change a persona's status or models, persist, and announce it.

    `status` accepts only `active`, `sick`, or `hibernate`. `thinking`,
    `vision`, `frontier` replace those models when given. `clear_vision`
    and `clear_frontier` explicitly remove a model (passing `None` is
    indistinguishable from "don't touch", so the explicit flag exists).

    This spec only mutates the persisted persona — it does not start or
    stop the agent. Lifecycle is the manager's concern.
    """
    bus.propose("Updating persona", {"persona": persona, "status": status})

    try:
        changed = False

        if status is not None:
            if status not in _ALLOWED_STATUS:
                bus.broadcast("Persona update failed", {"persona": persona, "reason": "invalid_status"})
                return Outcome(success=False, message=f"Status must be one of: {', '.join(sorted(_ALLOWED_STATUS))}.")
            if persona.status != status:
                persona.status = status
                changed = True

        if thinking is not None and persona.thinking != thinking:
            persona.thinking = thinking
            changed = True

        if clear_vision:
            if persona.vision is not None:
                persona.vision = None
                changed = True
        elif vision is not None and persona.vision != vision:
            persona.vision = vision
            changed = True

        if clear_frontier:
            if persona.frontier is not None:
                persona.frontier = None
                changed = True
        elif frontier is not None and persona.frontier != frontier:
            persona.frontier = frontier
            changed = True

        if changed:
            paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

        bus.broadcast("Persona updated", {"persona": persona, "status": persona.status})
        return Outcome(success=True, message="", data=UpdateData(persona=persona))

    except IdentityError as e:
        bus.broadcast("Persona update failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not save the persona's identity.")
