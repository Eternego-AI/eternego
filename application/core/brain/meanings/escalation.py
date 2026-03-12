"""Escalation — fallback meaning for unrecognized interactions."""

from application.core.brain.data import Meaning


class Escalation(Meaning):
    name = "Escalation"

    def description(self) -> str:
        return "Fallback for interactions that don't match any known meaning."

    def clarification(self) -> str:
        return ""

    def reply(self) -> str:
        return (
            "You encountered something you don't fully recognize. "
            "Ask a gentle, open-ended clarifying question to understand what the person needs. "
            "Be natural and curious, not robotic."
        )

    def path(self) -> list | None:
        return None

    async def run(self, persona_response: dict):
        return None
