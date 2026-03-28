"""Query — a direct programmatic query, no conversation."""

from application.core.brain.data import Meaning
from application.core import channels


class Query(Meaning):
    name = "Query"

    def description(self) -> str:
        return "A direct query from an external client expecting a single answer."

    def clarify(self) -> str | None:
        return None

    def reply(self) -> str | None:
        return None

    def summarize(self) -> str | None:
        return None

    def path(self) -> str | None:
        return (
            "Answer this query directly and concisely as the persona.\n"
            'Return JSON: {"response": "your answer"}'
        )

    async def run(self, persona_response: dict):
        """Send the response to all active channels and resolve."""
        text = persona_response.get("response", "")
        if not text:
            return None
        await channels.send_all(self.persona, text)
        return None
