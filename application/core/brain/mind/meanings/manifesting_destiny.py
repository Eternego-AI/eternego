"""Manifesting Destiny — a scheduled event or reminder is now due."""

import uuid
from pathlib import Path

from application.core.brain.data import Meaning, Signal
from application.core import paths
from application.platform import filesystem, logger


class ManifestingDestiny(Meaning):
    name = "Manifesting Destiny"

    def description(self) -> str:
        return (
            "A scheduled reminder or event is now due. "
            "The persona was nudged with the destiny entries that need to be fulfilled."
        )

    def clarify(self) -> str:
        return (
            "The previous attempt to fulfill the destiny entries failed. "
            "Look at the error — it could be a missing file, a path that no longer exists, "
            "or a permission issue. Let the person know the reminder or event was due "
            "regardless of the cleanup error."
        )

    def reply(self) -> str:
        return (
            "A reminder or scheduled event has come due. Notify the person naturally — "
            "tell them what it is and that it is time. Be warm and direct, not robotic. "
            "If there are multiple entries, mention each one."
        )

    def path(self) -> str | None:
        return (
            "Extract the destiny filenames from the conversation. "
            "Look for lines starting with 'File: ' followed by a filename.\n"
            'Return JSON: {"files": ["filename1.md", "filename2.md"]}\n'
            "List every filename mentioned in the destiny entries."
        )

    async def run(self, persona_response: dict):
        filenames = persona_response.get("files", [])
        if not filenames:
            return None

        destiny_dir = paths.destiny(self.persona.id)
        errors = []
        for name in filenames:
            target = destiny_dir / Path(name).name
            try:
                if target.exists():
                    filesystem.delete(target)
                    logger.info("manifesting_destiny: removed", {"file": str(target)})
            except Exception as e:
                errors.append(f"{name}: {e}")

        if errors:
            return Signal(
                id=str(uuid.uuid4()), role="user",
                content=f"Error removing destiny files: {'; '.join(errors)}",
            )
        return None
