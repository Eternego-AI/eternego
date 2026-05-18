"""Ability — take_screenshot.

Capture the current state of the persona's screen and return it as Media.
The clock executor passes the Media into add_tool_result, where the user-
role TOOL_RESULT message gets the image inlined for the next cognitive pass.

Pure observation: no input, no side effect on the screen. Use when the
person asks the persona to look at what's on screen.

The persona sees only the default monitor — other monitors don't exist
to her. The image is saved at logical resolution, capped at
`MAX_RETINA_EDGE` long edge so what we send fits the eye's effective
working size. After this ability runs, `living.view` carries the
landscape (the rect on the monitor she's looking at, in logical coords)
and the retina (the saved image's dimensions). Downstream abilities
(screen, locate) read `living.view` to translate the persona's
coordinates back into compositor space.

If the persona is asking for a sub-region (`dx > 0` and `dy > 0`), her
`(x, y, dx, dy)` are interpreted as monitor-local logical coords — a
rectangle within her default monitor's frame, (0, 0) at its top-left.
The ability never reads `living.view`; it only writes to it.

The eye runs a fixed scene-scan on every screenshot — apps, focus,
attention, dialogs, controls, motion. The persona doesn't choose what
the eye looks for; her sight always reports the same broad shape, the
way a human eye gives you a continuous sense of the room and lets the
moving thing pull your attention. The scan list lives in this file
(`SCAN`) and grows as we learn what else is worth a glance.
"""

from PIL import Image

from application.core import paths
from application.core.abilities import ability
from application.core.data import Media
from application.platform import OS, datetimes, filesystem, logger


MAX_RETINA_EDGE = 1500


SCAN = (
    "Describe what is on this screen using this checklist:\n\n"
    "- **Apps & windows**: which app or window is visible in the "
    "foreground?\n"
    "- **Attention pulls**: what is highlighted, selected, or visually "
    "emphasized right now?\n"
    "- **Modals & dialogs**: is any popup, modal, or alert showing? "
    "Describe its content.\n"
    "- **Interactive elements**: what visible buttons, links, fields, "
    "or controls are available?\n"
    "- **Risk surface**: any destructive or irreversible controls "
    "visible?\n"
    "- **Motion**: is anything mid-transition, loading, animating, or "
    "in progress?\n\n"
    "Do not claim keyboard focus from this image — focus is reported "
    "separately by the OS in the screenshot's tool-result."
)


@ability(
    "Capture a screenshot of your screen and look at it. Returns the image — "
    "on the next cycle your eye reports the scene: apps and focus, attention "
    "pulls, dialogs, available controls, and anything in motion. "
    "Pass x, y, dx, dy to zoom into a specific area of your screen; (x, y) is "
    "the top-left corner of the area, dx is the width, dy is the height. "
    "(0, 0) is the top-left of your screen. Omit them (or pass zero) to "
    "capture the full screen."
)
async def take_screenshot(living, x: int = 0, y: int = 0, dx: int = 0, dy: int = 0) -> Media:
    persona = living.ego.persona
    logger.debug("ability.take_screenshot", {"persona": persona, "x": x, "y": y, "dx": dx, "dy": dy})
    directory = paths.screenshots(persona.id)
    filesystem.ensure_dir(directory)
    target = str(directory / f"{datetimes.stamp(datetimes.now())}.png")

    mon_left, mon_top, mon_w, mon_h = await OS.default_monitor()

    # Decide what region to capture, expressed in compositor coords from
    # the start so `landscape` ends up in compositor space too. With
    # `(dx, dy)` the persona is naming a rectangle within her default
    # monitor — add the monitor offset to land in compositor. Without
    # them, capture the whole default monitor.
    if dx > 0 and dy > 0:
        region_x = mon_left + x
        region_y = mon_top + y
        region_w, region_h = dx, dy
    else:
        region_x, region_y = mon_left, mon_top
        region_w, region_h = mon_w, mon_h

    await OS.screenshot(left=region_x, top=region_y, width=region_w, height=region_h, path=target)

    # Cap the saved image at MAX_RETINA_EDGE long edge so what the eye
    # sees is what we send. Anthropic resizes anything bigger before the
    # model gets it, returning coordinates in its post-resize space —
    # capping ourselves keeps image-pixels and persona-pixels aligned.
    with Image.open(target) as img:
        retina_w, retina_h = img.size
        longest = max(retina_w, retina_h)
        if longest > MAX_RETINA_EDGE:
            factor = MAX_RETINA_EDGE / longest
            retina_w = int(retina_w * factor)
            retina_h = int(retina_h * factor)
            img.resize((retina_w, retina_h), Image.LANCZOS).save(target, "PNG")

    living.view["landscape"] = {"x": region_x, "y": region_y, "w": region_w, "h": region_h}
    living.view["retina"] = {"w": retina_w, "h": retina_h}
    return Media(source=target, caption="screenshot done", question=SCAN)
