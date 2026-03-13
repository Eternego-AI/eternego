"""Noting — the persona takes a note to remember something."""

import re
import uuid

from application.core.brain.data import Meaning, Signal
from application.core import paths
from application.platform import datetimes


class Noting(Meaning):
    name = "Noting"

    def description(self) -> str:
        return (
            "The person wants the persona to remember something — a preference, "
            "a fact, a decision, an instruction, or any piece of information "
            "worth keeping for future reference."
        )

    def clarify(self) -> str:
        return (
            "The previous attempt to save the note failed. "
            "Look at the error — it could be a missing title or content, "
            "an invalid filename, or a filesystem issue. "
            "Tell the person what went wrong and ask them to rephrase."
        )

    def reply(self) -> str:
        return "Acknowledge the note briefly. Confirm what you understood and that you will remember it."

    def summarize(self) -> str | None:
        return None

    def path(self) -> str | None:
        return (
            "Extract the note from this conversation.\n"
            'Return JSON: {"title": "short descriptive title", "content": "the full note"}\n'
            "The title should be a few words. The content is what to remember."
        )

    async def run(self, persona_response: dict):
        title = persona_response.get("title", "").strip()
        content = persona_response.get("content", "").strip()

        if not title or not content:
            return Signal(
                id=str(uuid.uuid4()), role="user",
                content="Error: title or content is missing.",
            )

        slug = re.sub(r"\W+", "-", title.lower()).strip("-")[:50]

        try:
            paths.write_as_string(
                paths.notes(self.persona.id) / f"{slug}-{datetimes.stamp(datetimes.now())}.md",
              f"# {title}\n\n{content}\n"
            )
        except Exception as e:
            return Signal(
                id=str(uuid.uuid4()), role="user",
                content=f"Error saving note: {e}",
            )

        return None
