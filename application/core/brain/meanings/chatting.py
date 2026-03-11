"""Chatting — regular casual conversation."""

from application.core.brain.meanings.meaning import Meaning


class Chatting(Meaning):
    name = "Chatting"

    def description(self) -> str:
        return "Regular casual conversation, small talk, sharing thoughts, or just talking."

    def clarification(self) -> str:
        return ""

    def reply(self) -> str:
        return (
            "Engage genuinely in the conversation. Be present, curious, and natural. "
            "Respond to what was actually said — don't deflect or over-explain. "
            "If something is interesting, say so. If you have a perspective, share it. "
            "Keep the exchange alive without dominating it."
        )

    def path(self) -> list | None:
        return None

    async def run(self, persona_response: dict):
        return None
