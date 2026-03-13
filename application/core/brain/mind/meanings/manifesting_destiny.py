"""Manifesting Destiny — a scheduled event or reminder is now due."""

import secrets
import uuid
from pathlib import Path

from application.core.brain.data import Meaning, Signal
from application.core import paths
from application.platform import datetimes, filesystem, logger


class ManifestingDestiny(Meaning):
    name = "Manifesting Destiny"

    def description(self) -> str:
        return (
            "A reminder or scheduled event that was due has been addressed. "
            "Clean up the fulfilled destiny entries and schedule next occurrences "
            "for recurring ones."
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

    def summarize(self) -> str | None:
        return None

    def path(self) -> str | None:
        return (
            "Look at the destiny entries in today's schedule from the current situation. "
            "Extract the filenames of entries that are now due or overdue.\n"
            "For each entry, check if it has recurrence info (e.g. 'recurrence: daily'). "
            "If recurring, calculate the next trigger time and preserve the full content "
            "including recurrence and timezone lines.\n\n"
            'Return JSON: {"entries": [\n'
            '  {"file": "filename.md", "next_trigger": "YYYY-MM-DD HH:MM", "next_timezone": "IANA timezone", "next_content": "full content with recurrence lines", "next_event": "reminder or schedule"}\n'
            "]}\n"
            "For non-recurring entries, omit next_trigger and related fields. "
            "Only include entries that are due now or overdue."
        )

    async def run(self, persona_response: dict):
        entries = persona_response.get("entries", [])
        if not entries:
            return None

        destiny_dir = paths.destiny(self.persona.id)
        errors = []

        for entry in entries:
            filename = entry.get("file", "")
            if filename:
                target = destiny_dir / Path(filename).name
                try:
                    if target.exists():
                        filesystem.delete(target)
                        logger.info("manifesting_destiny: removed", {"file": str(target)})
                except Exception as e:
                    errors.append(f"{filename}: {e}")

            next_trigger = entry.get("next_trigger", "")
            next_tz = entry.get("next_timezone", "")
            next_content = entry.get("next_content", "")
            next_event = entry.get("next_event", "schedule")

            if next_trigger and next_tz and next_content:
                try:
                    utc = datetimes.to_utc(next_trigger, next_tz)
                    paths.save_destiny_entry(
                        self.persona.id,
                        next_event,
                        utc.strftime("%Y-%m-%d %H:%M"),
                        secrets.token_hex(4),
                        next_content,
                    )
                    logger.info("manifesting_destiny: scheduled next", {"trigger": next_trigger, "content": next_content})
                except Exception as e:
                    errors.append(f"next occurrence: {e}")

        if errors:
            return Signal(
                id=str(uuid.uuid4()), role="user",
                content=f"Error: {'; '.join(errors)}",
            )
        return None
