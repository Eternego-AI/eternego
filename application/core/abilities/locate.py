"""Ability — locate.

Find the (x, y) of a named element on the current screen. The persona
names what she wants ("AI Mode button", "search input on the Google
homepage", "Submit link in the form"); the ability captures a screenshot
and hands it to realize with the locate-specific question attached. The
eye answers on the next cycle, and the coordinates land as a vision
tool-result the persona reads to plan her next screen action.

The cursor is parked at the center of the visible default monitor if it
was off-screen, so the eye has a reliable reference point for the dx/dy
distance it reports. If it was already on screen, it stays where it is —
the persona may have just acted and the cursor's current position is
meaningful.

The saved image is capped at `MAX_RETINA_EDGE` long edge — same rule as
take_screenshot — so what the eye answers about is what the persona's
coord system understands. `living.view` is updated with the landscape
(full default monitor in logical coords) and the retina (the saved
image's dimensions) so the persona's follow-up `screen.mouse_click`
lands where the eye said it would.
"""

from PIL import Image

from application.core import paths
from application.core.abilities import ability
from application.core.abilities.take_screenshot import MAX_RETINA_EDGE
from application.core.data import Media
from application.platform import OS, datetimes, desktop, filesystem, logger


@ability(
    "Find where a visible element is on the screen. Pass `target` — a "
    "description of the element you want to act on. The eye answers on the "
    "next cycle with the element's center coordinates and the distance from "
    "the cursor. Use the returned (x, y) with the screen ability to act on "
    "it. If your follow-up action doesn't land where you expected, call "
    "`locate` again — the new screenshot may show the target moved or the "
    "cursor drifted."
)
async def locate(living, target: str = "") -> Media:
    persona = living.ego.persona
    logger.debug("ability.locate", {"persona": persona, "target": target})
    if not target:
        raise ValueError("target is required")

    left, top, mon_w, mon_h = await OS.default_monitor()

    cx, cy = desktop.locate_cursor()
    if not (left <= cx < left + mon_w and top <= cy < top + mon_h):
        desktop.mouse_move(left + mon_w // 2, top + mon_h // 2)
        cx, cy = desktop.locate_cursor()

    directory = paths.screenshots(persona.id)
    filesystem.ensure_dir(directory)
    target_path = str(directory / f"{datetimes.stamp(datetimes.now())}-locate.png")
    await OS.screenshot(left=left, top=top, width=mon_w, height=mon_h, path=target_path)

    # Cap at MAX_RETINA_EDGE long edge so the eye's coord answers land in
    # the same pixel space the persona's view will use.
    with Image.open(target_path) as img:
        retina_w, retina_h = img.size
        longest = max(retina_w, retina_h)
        if longest > MAX_RETINA_EDGE:
            factor = MAX_RETINA_EDGE / longest
            retina_w = int(retina_w * factor)
            retina_h = int(retina_h * factor)
            img.resize((retina_w, retina_h), Image.LANCZOS).save(target_path, "PNG")

    cursor_local_x = cx - left
    cursor_local_y = cy - top
    question = (
        f"The cursor is at ({cursor_local_x}, {cursor_local_y}) on this screen. "
        f"Where is '{target}'? "
        "Return its center coordinates as `x=<N> y=<N>` and the distance "
        "from the cursor as `dx=<N> dy=<N>`. If you can't find it, say so plainly."
    )
    # Landscape in compositor coords — origin at the monitor's compositor
    # offset so screen can act on the persona's coords without re-querying
    # the monitor geometry.
    living.view["landscape"] = {"x": left, "y": top, "w": mon_w, "h": mon_h}
    living.view["retina"] = {"w": retina_w, "h": retina_h}
    return Media(source=target_path, caption="locate done", question=question)
