"""Ability — screen.

One ability that wraps every desktop input verb (click, drag, type, press
keys, scroll, …) and returns a screenshot of the resulting state. The
persona acts and sees the result on the next cognitive pass — one cycle,
one observation, one decision.

Dispatches to `application/platform/desktop.py` by action name. The clock
executor takes the Media returned here and inlines the screenshot into the
TOOL_RESULT message via memory.add_tool_result.
"""

from PIL import Image

from application.core import paths, tools
from application.core.abilities import ability
from application.core.data import Media
from application.platform import OS, datetimes, filesystem, logger


@ability(
    "Act on your screen and see the result. action is one of the desktop "
    "input verbs (mouse_move, mouse_click, mouse_drag, mouse_press, "
    "mouse_release, mouse_scroll, keyboard_type, keyboard_tap, keyboard_press, "
    "keyboard_release); pass the verb's own kwargs flat alongside action — "
    "shape is `{\"tools.screen\": {\"action\": \"<verb>\", <verb's kwargs>}}`. "
    "Coordinates are in screenshot-pixel space (the image you last saw); "
    "this ability translates them into display-pixel space before dispatching. "
    "See each `tools.desktop.<verb>` entry above for that verb's parameters. "
    "Returns a screenshot — you see the screen after the action on the next "
    "cycle. Your environment notes whether a display is currently available; "
    "if it is not, this ability will fail and you should tell the person "
    "rather than retry."
)
async def screen(persona, action: str = "", **args) -> Media:
    logger.debug("ability.screen", {"persona": persona, "action": action, "args": args})
    if not action:
        raise ValueError("action is required")
    action = action.removeprefix("desktop.")

    # Translate screenshot-pixel coordinates into display-pixel coordinates.
    # The persona sees the screen at 1280px longest dim (downscaled below);
    # she gives clicks in that space. We scale every kwarg whose name starts
    # with `x` or `y` — that's the desktop module's convention for pixel
    # positions. Scroll deltas (`dx`, `dy`) and everything else pass through.
    display_w, display_h = await OS.default_screen_size()
    scale = max(display_w, display_h) / 1280 if max(display_w, display_h) > 1280 else 1.0
    scaled = {
        k: (int(v * scale) if (k.startswith("x") or k.startswith("y")) and isinstance(v, (int, float)) else v)
        for k, v in args.items()
    }

    status, result = await tools.call(f"desktop.{action}", **scaled)
    if status != "ok":
        raise RuntimeError(f"{action} failed: {result}")
    directory = paths.screenshots(persona.id)
    filesystem.ensure_dir(directory)
    target = str(directory / f"{datetimes.stamp(datetimes.now())}.png")
    await OS.screenshot(path=target)

    # Cap longest dim at 1280 — must match the screenshot space the persona
    # works in, so her next coordinate guesses scale by the same factor.
    with Image.open(target) as img:
        if max(img.width, img.height) > 1280:
            img.thumbnail((1280, 1280), Image.LANCZOS)
            img.save(target)

    return Media(source=target, caption=result)
