"""Ability — take_screenshot.

Capture the current state of the persona's screen and return it as Media.
The clock executor passes the Media into add_tool_result, where the user-
role TOOL_RESULT message gets the image inlined for the next cognitive pass.

Pure observation: no input, no side effect on the screen. Use when the
person asks the persona to look at what's on screen.
"""

from application.core import paths
from application.core.abilities import ability
from application.core.data import Media
from application.platform import OS, datetimes, filesystem, logger


@ability(
    "Capture a screenshot of your screen and look at it. Returns the image — "
    "you will see what is on screen on the next cycle. Your environment notes "
    "whether a display is currently available; if it is not, this ability will "
    "fail and you should tell the person rather than retry."
)
async def take_screenshot(persona) -> Media:
    logger.debug("ability.take_screenshot", {"persona": persona})
    directory = paths.screenshots(persona.id)
    filesystem.ensure_dir(directory)
    target = str(directory / f"{datetimes.stamp(datetimes.now())}.png")
    OS.screenshot(path=target)
    return Media(source=target, caption="screenshot")
