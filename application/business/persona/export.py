"""Persona — export a persona's diary for migration."""

from application.business.outcome import Outcome
from application.core import bus
from application.core.exceptions import DiaryError, IdentityError, SecretStorageError, UnsupportedOS

from .find import find
from .write_diary import write_diary


async def export(persona_id: str) -> Outcome[dict]:
    """Write the persona's diary and return the file path for download. Persona must be stopped."""
    await bus.propose("Exporting persona", {"persona_id": persona_id})

    try:
        outcome = await find(persona_id)
        if not outcome.success:
            return outcome

        persona = outcome.data["persona"]

        outcome = await write_diary(persona)
        if not outcome.success:
            await bus.broadcast("Export failed", {"persona_id": persona_id, "reason": "diary", "error": outcome.message})
            return outcome

        await bus.broadcast("Persona exported", {"persona_id": persona_id})
        return Outcome(
            success=True,
            message="Persona exported successfully",
            data={
                "persona_id": persona_id,
                "name": persona.name,
                "diary_path": outcome.data["diary_path"],
            },
        )

    except (UnsupportedOS, SecretStorageError, DiaryError, IdentityError) as e:
        await bus.broadcast("Export failed", {"persona_id": persona_id, "error": str(e)})
        return Outcome(success=False, message=str(e))
