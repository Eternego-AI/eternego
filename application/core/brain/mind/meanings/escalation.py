"""Escalation — fallback when no existing meaning matches the interaction."""

from application.core.brain.data import Meaning


class Escalation(Meaning):
    name = "Escalation"

    def description(self) -> str:
        return (
            "The interaction does not match any known meaning. "
            "Use this when the person's request, topic, or intent falls outside "
            "everything else available."
        )

    def clarification(self) -> str:
        return ""

    def reply(self) -> str:
        return (
            "You don't fully understand what the person needs yet. "
            "Ask a gentle, open-ended clarifying question to learn more. "
            "Be curious and natural, not robotic or apologetic."
        )

    def path(self) -> str | None:
        return None
