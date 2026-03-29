"""Recalling — the persona recalls a past conversation from history."""

from pathlib import Path

from application.core.brain.data import Meaning
from application.core import paths
from application.platform import filesystem


class Recalling(Meaning):
    name = "Recalling"

    def description(self) -> str:
        return (
            "The person wants to recall, revisit, or reference a past conversation — "
            "something they discussed before, a decision that was made, "
            "or context from a previous interaction."
        )

    def clarify(self) -> str:
        return (
            "A history lookup has completed. Look at the result in the conversation. "
            "If conversations were found, summarize the key points naturally — "
            "what was discussed, what was decided, what happened. "
            "If nothing was found, let the person know and suggest they rephrase."
        )

    def reply(self) -> str | None:
        return None

    def summarize(self) -> str | None:
        return None

    def path(self) -> str | None:
        briefing_path = paths.history_briefing(self.persona.id)
        if not briefing_path.exists():
            return None

        listing = filesystem.read(briefing_path).strip()
        if not listing:
            return None

        return (
            "The person wants to recall a past conversation.\n\n"
            f"## Past Conversations\n\n{listing}\n\n"
            "Select the file that best matches what the person is asking about.\n"
            'Return JSON: {"file": "filename.md"}\n'
            "Pick only the most relevant file."
        )

    async def run(self, persona_response: dict):
        filename = persona_response.get("file", "")
        history_dir = paths.history(self.persona.id)

        async def action():
            if not filename:
                return "No matching conversations found in history."

            target = history_dir / Path(filename).name
            if not target.exists():
                return "Could not find the requested history file."

            text = filesystem.read(target).strip()
            if not text:
                return "The history file is empty."

            return f"## {filename}\n\n{text}"

        return action
