"""Meaning — chatting."""

from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Any type of conversation, there is nothing to do but talk"

    def path(self) -> str:
        return (
            "Be with the person through words. You already know who they are — their traits, "
            "their wishes, their struggles, how you stand with them, what you have carried "
            "forward from earlier conversations. Attend to what was said and respond from "
            "that knowledge.\n\n"
            "Use `say` to reply on the current channel. If nothing is ready to be said, "
            "return `done`."
        )
