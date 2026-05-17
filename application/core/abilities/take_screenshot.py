"""Ability — take_screenshot.

Capture the current state of the persona's screen and return it as Media.
The clock executor passes the Media into add_tool_result, where the user-
role TOOL_RESULT message gets the image inlined for the next cognitive pass.

Pure observation: no input, no side effect on the screen. Use when the
person asks the persona to look at what's on screen.

The persona sees only the default monitor — other monitors don't exist
to her. All coordinates she passes are in default-monitor space, with
(0, 0) at that monitor's top-left.
"""

from application.core import paths
from application.core.abilities import ability
from application.core.data import Media
from application.platform import OS, datetimes, filesystem, logger


@ability(
    "Capture a screenshot of your screen and look at it. Returns the image — "
    "you will see what is on screen on the next cycle. "
    "Pass x, y, dx, dy to zoom into a specific area; (x, y) is the top-left "
    "corner of the area, dx is the width, dy is the height. Coords match the "
    "image you last saw, with (0, 0) at the top-left of your screen. Omit "
    "them (or pass zero) to capture the full screen."
)
async def take_screenshot(persona, x: int = 0, y: int = 0, dx: int = 0, dy: int = 0) -> Media:
    logger.debug("ability.take_screenshot", {"persona": persona, "x": x, "y": y, "dx": dx, "dy": dy})
    directory = paths.screenshots(persona.id)
    filesystem.ensure_dir(directory)
    target = str(directory / f"{datetimes.stamp(datetimes.now())}.png")

    # Translate default-monitor-local coords into compositor coords by
    # adding the monitor's (left, top) offset. With no region requested,
    # capture the whole default monitor.
    left, top, mon_w, mon_h = await OS.default_monitor()
    if dx > 0 and dy > 0:
        await OS.screenshot(left=left + x, top=top + y, width=dx, height=dy, path=target)
    else:
        await OS.screenshot(left=left, top=top, width=mon_w, height=mon_h, path=target)

    return Media(source=target, caption="screenshot")
