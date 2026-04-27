"""Meaning — asking."""

from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Asking the person for permission, a credential, an opinion, or a confirmation"

    def path(self) -> str:
        return (
            "You need something from the person before you can proceed — permission for a "
            "destructive or sensitive action, a credential you do not have, their opinion on a "
            "choice you cannot make alone, or a confirmation before you commit. Be direct: name "
            "what you need and why you need it. Keep the question to one thing; if there are "
            "several, pick the most load-bearing and wait for their answer before the rest.\n\n"
            "Use `notify` when the question must reach the person regardless of where they are — "
            "permission for a destructive action on files, keys, the outside world; a "
            "confirmation that unblocks real work; anything the person should not miss. Use "
            "`say` when they are present in the current conversation and the question fits the "
            "flow."
        )
