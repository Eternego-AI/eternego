"""Persona — export a persona's diary for migration."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus
from application.core.exceptions import DiaryError, IdentityError, SecretStorageError, UnsupportedOS
from application.core.data import Persona

from .write_diary import write_diary


@dataclass
class ExportData:
    persona: Persona
    diary_path: str


async def export(persona: Persona) -> Outcome[ExportData]:
    """Write the persona's diary and return the file path for download. Persona must be stopped."""
    bus.propose("Exporting persona", {"persona": persona})

    try:
        outcome = await write_diary(persona)
        if not outcome.success:
            bus.broadcast("Export failed", {"persona": persona, "reason": "diary", "error": outcome.message})
            return Outcome(success=False, message=outcome.message, data=ExportData(persona=persona, diary_path=""))

        bus.broadcast("Persona exported", {"persona": persona})
        return Outcome(
            success=True,
            message="Persona exported successfully",data=ExportData(persona=persona, diary_path=outcome.data.diary_path))

    except (UnsupportedOS, SecretStorageError, DiaryError, IdentityError) as e:
        bus.broadcast("Export failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
