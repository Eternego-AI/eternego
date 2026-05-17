"""Ability — screen.

The single entry point for the persona's desktop input. Wraps every
`application/platform/desktop` verb (click, drag, type, press keys,
scroll, …) and returns a screenshot of the resulting state. The persona
acts and sees the result on the next cognitive pass — one cycle, one
observation, one decision.

The persona never talks to `desktop.*` directly. Two reasons:
- coord-space discipline: desktop verbs take compositor coords; the
  persona thinks in default-monitor-local coords (what she sees in her
  screenshot). This ability owns the translation in one place.
- one surface: every input + visual feedback flows through one verb,
  which keeps the persona's mental model small.

The clock executor takes the Media returned here and inlines the
screenshot into the TOOL_RESULT message via memory.add_tool_result.
"""

from application.core.abilities import ability
from application.core.abilities.take_screenshot import take_screenshot
from application.core.data import Media
from application.platform import OS, desktop, logger


@ability(
    "Drive your desktop one step at a time, with visual feedback. You name "
    "one action; the ability runs it and returns a screenshot of the "
    "resulting state. You read the screenshot on the next cycle and decide "
    "what comes next.\n\n"
    "Shape: `{\"tools.screen\": {\"action\": \"<verb>\", <verb's kwargs>}}`. "
    "Every `x`, `y`, `x_from`, `y_from`, `x_to`, `y_to` is in the coordinate "
    "space of the screenshot you last saw — (0, 0) is the top-left of your "
    "screen. Button names, key names, modifiers, and chord syntax live in "
    "your environment notes.\n\n"
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
async def screen(persona, action: str = "", **args) -> Media:
    logger.debug("ability.screen", {"persona": persona, "action": action, "args": args})
    if not action:
        raise ValueError("action is required")
    action = action.removeprefix("desktop.")
    fn = getattr(desktop, action, None)
    if not callable(fn):
        raise ValueError(f"unknown action: {action}")

    # Translate default-monitor-local coords into compositor coords by
    # adding the monitor's (left, top) offset so the cursor lands inside
    # the default monitor. Every kwarg whose name starts with `x` or `y`
    # is treated as a position. Scroll deltas (`dx`, `dy`) and everything
    # else pass through.
    left, top, _, _ = await OS.default_monitor()
    translated = {}
    for k, v in args.items():
        if isinstance(v, (int, float)) and (k.startswith("x") or k.startswith("y")):
            offset = left if k.startswith("x") else top
            translated[k] = int(v) + offset
        else:
            translated[k] = v

    result = fn(**translated)
    media = await take_screenshot(persona)
    return Media(source=media.source, caption=result)
