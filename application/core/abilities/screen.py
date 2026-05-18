"""Ability — screen.

The single entry point for the persona's desktop input. Wraps every
`application/platform/desktop` verb (click, drag, type, press keys,
scroll, …) and returns a screenshot of the resulting state. The persona
acts and sees the result on the next cognitive pass — one cycle, one
observation, one decision.

The persona never talks to `desktop.*` directly. Two reasons:
- coord-space discipline: desktop verbs take compositor coords; the
  persona thinks in the image she last saw. The translation from her
  retina-space coords through landscape-space to compositor-space lives
  here, in one formula.
- one surface: every input + visual feedback flows through one verb,
  which keeps the persona's mental model small.

Coordinate translation: `living.view["landscape"]` is the rectangle on
the default monitor the persona is looking at (logical coords).
`living.view["retina"]` is her saved image's dimensions. Her `x`/`y`
args are in retina space; we scale them through to landscape, add the
monitor's compositor offset, and write to the EV_ABS device.

Bounds check: an action coord that maps outside the landscape rectangle
is refused — the persona is trying to act on something she can't see.
She must re-screenshot before re-acting. Similarly, if she has no view
yet (first beat after wake), screen refuses until she takes a
screenshot.
"""

from application.core.abilities import ability
from application.core.abilities.take_screenshot import take_screenshot
from application.core.data import Media
from application.platform import desktop, logger


@ability(
    "Drive your desktop one step at a time, with visual feedback. You name "
    "one action; the ability runs it and returns a screenshot of the "
    "resulting state. You read the screenshot on the next cycle and decide "
    "what comes next.\n\n"
    "Shape: `{\"tools.screen\": {\"action\": \"<verb>\", <verb's kwargs>}}`. "
    "Every `x`, `y`, `x_from`, `y_from`, `x_to`, `y_to` is in the coordinate "
    "space of the screenshot you last saw — (0, 0) is the top-left of your "
    "screen. When you don't already have a coordinate for what you want to "
    "act on, call `tools.locate` first to find it — guessing from the "
    "screenshot misses the target. Button names, key names, modifiers, and "
    "chord syntax live in your environment notes.\n\n"
    "Actions:\n"
    "- `mouse_move(x, y)` — move the cursor to (x, y).\n"
    "- `mouse_click(x, y, button, count)` — click at (x, y). count is 1 "
    "for single click, 2 for double-click.\n"
    "- `mouse_drag(x_from, y_from, x_to, y_to, button)` — press at the "
    "from-point, drag to the to-point, release.\n"
    "- `mouse_press(x, y, button)` — press a button at (x, y) without "
    "releasing it. Pair with `mouse_release`.\n"
    "- `mouse_release(x, y, button)` — release a held button at (x, y).\n"
    "- `mouse_scroll(x, y, dx, dy)` — scroll at (x, y). Positive dy "
    "scrolls up, negative dy scrolls down; dx scrolls horizontally.\n"
    "- `keyboard_type(text)` — type a string at whatever has keyboard focus.\n"
    "- `keyboard_tap(key)` — press and release a single key or chord.\n"
    "- `keyboard_press(key)` — press a key without releasing it. Pair "
    "with `keyboard_release`.\n"
    "- `keyboard_release(key)` — release a held key."
)
async def screen(living, action: str = "", **args) -> Media:
    logger.debug("ability.screen", {"persona": living.ego.persona, "action": action, "args": args})
    if not action:
        raise ValueError("action is required")
    landscape = living.view.get("landscape")
    retina = living.view.get("retina")
    if not landscape or not retina:
        raise ValueError(
            "no view yet — take a screenshot before acting so you can see "
            "what you're addressing"
        )
    action = action.removeprefix("desktop.")
    fn = getattr(desktop, action, None)
    if not callable(fn):
        raise ValueError(f"unknown action: {action}")

    scale_x = landscape["w"] / retina["w"]
    scale_y = landscape["h"] / retina["h"]

    # Translate every position-kwarg (anything whose name starts with x or y)
    # from the persona's retina space through landscape to compositor coords.
    # Landscape is already in compositor coords, so no extra monitor-offset
    # step. Bounds-check against the landscape rectangle: if the mapped point
    # isn't inside what she can see, refuse — she'd be acting blind.
    translated = {}
    for k, v in args.items():
        if isinstance(v, (int, float)) and k.startswith("x"):
            compositor_x = landscape["x"] + int(v * scale_x)
            if not (landscape["x"] <= compositor_x < landscape["x"] + landscape["w"]):
                raise ValueError(
                    f"{k}={v} maps outside your current view "
                    f"(landscape x spans {landscape['x']}..{landscape['x'] + landscape['w']}). "
                    "Take a fresh screenshot to refresh what you can address."
                )
            translated[k] = compositor_x
        elif isinstance(v, (int, float)) and k.startswith("y"):
            compositor_y = landscape["y"] + int(v * scale_y)
            if not (landscape["y"] <= compositor_y < landscape["y"] + landscape["h"]):
                raise ValueError(
                    f"{k}={v} maps outside your current view "
                    f"(landscape y spans {landscape['y']}..{landscape['y'] + landscape['h']}). "
                    "Take a fresh screenshot to refresh what you can address."
                )
            translated[k] = compositor_y
        else:
            translated[k] = v

    fn(**translated)

    # Post-action screenshot. take_screenshot caps if needed and updates
    # living.view, so the next action lands in the right coord space.
    media = await take_screenshot(living)
    return Media(source=media.source, caption=f"{action} done", question=media.question)
