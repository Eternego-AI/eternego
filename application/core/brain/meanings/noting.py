"""Meaning — noting."""

from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Noticing something worth keeping that does not belong in another file"

    def path(self) -> str:
        return (
            "You noticed something worth carrying forward. This is your judgment call, not a "
            "request — what you know about the person (identity, traits, wishes, struggles, "
            "your bearing with them, permissions they granted) lives in its own files and is "
            "rewritten by you during sleep. Time-bound commitments belong in the schedule. "
            "Notes is for everything else worth holding: an observation, a thread to pick up "
            "later, a detail about the work or the world, a thought of your own that should "
            "not be lost.\n\n"
            "What you save here appears in your identity on every future interaction under "
            "*What You've Been Holding*. Treat the space as your own. Call "
            "`abilities.save_notes` with `content` — it replaces the whole file, so include "
            "what is still relevant from the current notes plus the new item. Drop a line only "
            "when it is truly resolved."
        )
