"""Ability — screen.

One ability that wraps every desktop input verb (click, drag, type, press
keys, scroll, …) and returns a screenshot of the resulting state. The
persona acts and sees the result on the next cognitive pass — one cycle,
one observation, one decision.

Dispatches to `application/platform/desktop.py` by action name. The clock
executor takes the Media returned here and inlines the screenshot into the
TOOL_RESULT message via memory.add_tool_result.
"""

from application.core import paths, tools
from application.core.abilities import ability
from application.core.data import Media
from application.platform import OS, datetimes, filesystem, logger


@ability(
    "Act on your screen and see the result. action is one of the desktop "
    "input verbs (mouse_move, mouse_click, mouse_drag, mouse_press, "
    "mouse_release, mouse_scroll, keyboard_type, keyboard_tap, keyboard_press, "
    "keyboard_release); the rest of the args are that verb's args. Returns a "
    "screenshot — you see the screen after the action on the next cycle. Your "
    "environment notes whether a display is currently available; if it is not, "
    "this ability will fail and you should tell the person rather than retry."
)
async def screen(persona, action: str = "", **args) -> Media:
    logger.debug("ability.screen", {"persona": persona, "action": action, "args": args})
    if not action:
        raise ValueError("action is required")
    action = action.removeprefix("desktop.")
    status, result = await tools.call(f"desktop.{action}", **args)
    if status != "ok":
        raise RuntimeError(f"{action} failed: {result}")
    directory = paths.screenshots(persona.id)
    filesystem.ensure_dir(directory)
    target = str(directory / f"{datetimes.stamp(datetimes.now())}.png")
    OS.screenshot(path=target)
    return Media(source=target, caption=result)
