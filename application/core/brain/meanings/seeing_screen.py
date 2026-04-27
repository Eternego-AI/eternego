"""Meaning — seeing_screen."""

from application.core import paths
from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Looking at what is on the person's screen right now"

    def path(self) -> str:
        media_dir = str(paths.media(self.persona.id))
        return (
            "The person wants you to look at their screen. First, capture a screenshot into "
            f"your media directory (`{media_dir}`) using `tools.OS.screenshot` with all-zero "
            "coordinates for a full grab and an explicit `path` like "
            f"`{media_dir}/<timestamp>.png`. On the next cycle, you will see the TOOL_RESULT "
            "with the saved path. Then call `abilities.look_at` with that `source` and a "
            "precise `question` tied to what the person asked. On the cycle after, reply with `say`."
        )
