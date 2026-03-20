"""Recalling — the persona recalls a past conversation from history."""

import uuid
from pathlib import Path

from application.core.brain.data import Meaning, Signal, SignalEvent
from application.core import paths
from application.platform import filesystem, logger


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
        history_dir = paths.history(self.persona.id)
        if not history_dir.exists():
            return None

        files = [f for f in sorted(history_dir.glob("*.md")) if f.name != "briefing.md"]
        if not files:
            return None

        listing = "\n".join(f"- {f.name}" for f in files)
        return (
            "The person wants to recall a past conversation.\n\n"
            f"## History\n\n{listing}\n\n"
            "Select the files that best match what the person is asking about.\n"
            'Return JSON: {"files": ["filename1.md", "filename2.md"]}\n'
            "Pick only the most relevant files."
        )

    async def run(self, persona_response: dict):
        filenames = persona_response.get("files", [])
        if not filenames:
            return Signal(
                id=str(uuid.uuid4()), event=SignalEvent.executed,
                content="No matching conversations found in history.",
            )

        history_dir = paths.history(self.persona.id)
        contents = []
        for name in filenames:
            target = history_dir / Path(name).name
            if target.exists():
                text = filesystem.read(target).strip()
                if text:
                    contents.append(f"## {name}\n\n{text}")

        if not contents:
            return Signal(
                id=str(uuid.uuid4()), event=SignalEvent.executed,
                content="Could not find the requested history files.",
            )

        return Signal(
            id=str(uuid.uuid4()), event=SignalEvent.executed,
            content="\n\n---\n\n".join(contents),
        )
