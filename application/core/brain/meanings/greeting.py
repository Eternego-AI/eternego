"""Greeting — daily greetings and salutations."""

from application.core.brain.meanings.meaning import Meaning


class Greeting(Meaning):
    name = "Greeting"

    def description(self) -> str:
        return "Daily greetings, hellos, good mornings, and other salutations."

    def clarification(self) -> str:
        return ""

    def reply(self) -> str:
        return (
            "Greet the person warmly and naturally. Match their energy and tone. "
            "Keep it brief — a greeting deserves a greeting, not a speech. "
            "You may ask how they are or what's on their mind, but don't pepper them with questions."
        )

    def path(self) -> list | None:
        return None

    async def run(self, persona_response: dict):
        return None
