"""Calendar — the person wants to check what is on their calendar."""

import re
import uuid

from application.core.brain.data import Meaning, Signal
from application.core import paths
from application.platform import logger


class Calendar(Meaning):
    name = "Calendar"

    def description(self) -> str:
        return (
            "The person wants to know what is on their calendar — "
            "upcoming reminders, scheduled events, or appointments "
            "for a specific date, date range, or today."
        )

    def clarify(self) -> str:
        return (
            "The calendar has been checked. Look at the result in the conversation. "
            "If entries were found, present them naturally — mention the date, time, "
            "and what each one is about. "
            "If no entries were found, let the person know their calendar is clear. "
            "If there was an error, explain what went wrong and ask them to rephrase."
        )

    def reply(self) -> str | None:
        return None

    def summarize(self) -> str | None:
        return None

    def path(self) -> str | None:
        return (
            "Extract the date range the person is asking about.\n"
            'Return JSON: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}\n'
            "Use the same date for both if asking about a single day."
        )

    async def run(self, persona_response: dict):
        start = persona_response.get("start", "")
        end = persona_response.get("end", "")

        if not start or not end:
            return Signal(
                id=str(uuid.uuid4()), role="user",
                content="Error: start or end date is missing.",
            )

        destiny_dir = paths.destiny(self.persona.id)
        if not destiny_dir.exists():
            return Signal(
                id=str(uuid.uuid4()), role="user",
                content="Calendar is empty — no reminders or events scheduled.",
            )

        entries = []
        for f in sorted(destiny_dir.glob("*.md")):
            match = re.search(r"(\d{4}-\d{2}-\d{2})-\d{2}-\d{2}", f.name)
            if not match:
                continue
            file_date = match.group(1)
            if start <= file_date <= end:
                content = f.read_text().strip()
                kind = "reminder" if f.name.startswith("reminder") else "event"
                time_match = re.search(r"\d{4}-(\d{2}-\d{2})-(\d{2})-(\d{2})", f.name)
                time_str = f"{time_match.group(2)}:{time_match.group(3)}" if time_match else ""
                entries.append(f"{file_date} {time_str} [{kind}] {content}")

        if not entries:
            return Signal(
                id=str(uuid.uuid4()), role="user",
                content=f"No reminders or events found between {start} and {end}.",
            )

        return Signal(
            id=str(uuid.uuid4()), role="user",
            content=f"Calendar entries ({start} to {end}):\n" + "\n".join(entries),
        )
