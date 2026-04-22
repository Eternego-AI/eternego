"""Meaning — looking at the screen."""

from application.core import paths
from application.core.data import Persona


class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "Looking at the person's screen"

    def prompt(self) -> str:
        media_dir = str(paths.media(self.persona.id))
        return (
            "The person asked you to look at their screen. Take a screenshot, save it to your "
            "media, then look at it with a precise question that helps the vision model focus on "
            "what the person is asking about.\n\n"
            "## Tools\n\n"
            "- `OS.screenshot(left, top, width, height, path)` — capture the screen. All zeros for full screen.\n"
            "- `look_at(source, question)` — look at the captured image with a specific question.\n"
            "- `say(text)` — message the person.\n\n"
            "## When the person first asks you\n\n"
            f"Take a screenshot and save it to your media directory: `{media_dir}`\n\n"
            "### Response Format\n\n"
            "```json\n"
            '{'
            ' "tool": "OS.screenshot",\n'
            ' "left": 0, "top": 0, "width": 0, "height": 0,\n'
            f' "path": "{media_dir}/<timestamp>.png"}}\n'
            "```\n\n"
            "## When the screenshot is taken\n\n"
            "You will see a `TOOL_RESULT` for `OS.screenshot` with the saved path. Now prepare a "
            "question for the vision model — be specific about what to look for based on what the "
            "person asked. A precise question gets a precise answer.\n\n"
            "### Response Format\n\n"
            "```json\n"
            '{'
            ' "tool": "look_at",\n'
            ' "source": "<path from the screenshot result>",\n'
            ' "question": "<precise question that helps vision focus>"}\n'
            "```\n\n"
            "## When you have seen the image\n\n"
            "You will see a `TOOL_RESULT` for `vision` with the description. Answer the person "
            "based on what you saw. If you need to zoom into a specific area, take another "
            "screenshot with coordinates.\n\n"
            "### Response Format\n\n"
            "```json\n"
            '{'
            ' "tool": "say",\n'
            ' "text": "<your answer to the person>"}\n'
            "```"
        )
