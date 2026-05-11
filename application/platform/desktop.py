"""Desktop — keyboard and mouse input primitives.

macOS and Windows go through `pynput` (Quartz on macOS, SendInput on
Windows). Linux goes through the kernel's /dev/uinput device via the
`evdev` library — same path on X11 and Wayland sessions, since uinput
is below the display server, not on top of it.

Composition (drag, chord taps, click-and-screenshot) lives one layer up.
Screen capture lives in `OS.screenshot` — it's a system operation, not
an input verb, so the abilities call it directly rather than through here.

Chord-key name resolution lives in `keyboard.resolve` so the alias names
are owned in one place and surfaced once to the persona via the
environment prompt.

Linux requires write access to /dev/uinput. The persona's user must
either be in the `input` group, or a udev rule must grant access.

Imports are lazy inside each function — instantiating pynput on Linux
crashes on a Wayland session, and importing evdev on macOS/Windows
would fail at module-load time.
"""

import time

from application.platform import keyboard
from application.platform.OS import get_supported
from application.platform.tool import tool


# Module-level cache of the lazy-opened UInput device. Each Linux verb
# below opens it on first use (the same dance is duplicated across verbs
# rather than extracted, so each verb reads top-to-bottom).
uinput_device = None


@tool("Move the mouse cursor to absolute screen coordinates (x, y in pixels). "
      "Use the screenshot's pixel space — top-left is (0, 0).")
def mouse_move(x: int, y: int) -> str:
    if get_supported() == "linux":
        from evdev import UInput, ecodes as e
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        # Slam cursor to (0,0) via massive relative move, then move to target —
        # uinput has no absolute pointer registered, and Wayland exposes no API
        # to query current cursor position, so this is the standard trick.
        # The two syn() calls are load-bearing: relative events within a single
        # syn batch accumulate as one net delta, so without the intermediate
        # syn the compositor sees `(-10000 + x, -10000 + y)` — a huge negative
        # delta that clamps the cursor to (0, 0) regardless of x/y. The slam
        # must commit first so the second batch starts from origin.
        ui.write(e.EV_REL, e.REL_X, -10000)
        ui.write(e.EV_REL, e.REL_Y, -10000)
        ui.syn()
        time.sleep(0.05)
        ui.write(e.EV_REL, e.REL_X, int(x))
        ui.write(e.EV_REL, e.REL_Y, int(y))
        ui.syn()
    else:
        from pynput.mouse import Controller
        Controller().position = (int(x), int(y))
    return f"moved to ({x}, {y})"


@tool("Click the mouse at the cursor's current position. button is 'left', 'right', or 'middle' "
      "(default 'left'). count is 1 for single click, 2 for double-click.")
def mouse_click(button: str = "left", count: int = 1) -> str:
    name = (button or "left").strip().lower()
    if get_supported() == "linux":
        from evdev import UInput, ecodes as e
        codes = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}
        code = codes.get(name)
        if code is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        for _ in range(int(count)):
            ui.write(e.EV_KEY, code, 1)
            ui.syn()
            ui.write(e.EV_KEY, code, 0)
            ui.syn()
    else:
        from pynput.mouse import Controller, Button
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
        if btn is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        Controller().click(btn, int(count))
    return f"{button} click x{count}"


@tool("Drag the mouse from (from_x, from_y) to (to_x, to_y) while holding a button. "
      "button is 'left', 'right', or 'middle' (default 'left').")
def mouse_drag(from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> str:
    name = (button or "left").strip().lower()
    if get_supported() == "linux":
        from evdev import UInput, ecodes as e
        codes = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}
        code = codes.get(name)
        if code is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        # Move to start
        ui.write(e.EV_REL, e.REL_X, -10000)
        ui.write(e.EV_REL, e.REL_Y, -10000)
        ui.write(e.EV_REL, e.REL_X, int(from_x))
        ui.write(e.EV_REL, e.REL_Y, int(from_y))
        ui.syn()
        # Press button, drag, release
        ui.write(e.EV_KEY, code, 1)
        ui.syn()
        ui.write(e.EV_REL, e.REL_X, int(to_x) - int(from_x))
        ui.write(e.EV_REL, e.REL_Y, int(to_y) - int(from_y))
        ui.syn()
        ui.write(e.EV_KEY, code, 0)
        ui.syn()
    else:
        from pynput.mouse import Controller, Button
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
        if btn is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        mouse = Controller()
        mouse.position = (int(from_x), int(from_y))
        mouse.press(btn)
        mouse.position = (int(to_x), int(to_y))
        mouse.release(btn)
    return f"dragged ({from_x}, {from_y}) → ({to_x}, {to_y}) with {button}"


@tool("Press a mouse button without releasing it. Pair with mouse_release; in between, "
      "use mouse_move to drive the held-button movement. button: 'left', 'right', 'middle'.")
def mouse_press(button: str = "left") -> str:
    name = (button or "left").strip().lower()
    if get_supported() == "linux":
        from evdev import UInput, ecodes as e
        codes = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}
        code = codes.get(name)
        if code is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        ui.write(e.EV_KEY, code, 1)
        ui.syn()
    else:
        from pynput.mouse import Controller, Button
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
        if btn is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        Controller().press(btn)
    return f"{button} button down"


@tool("Release a previously held mouse button. button: 'left', 'right', 'middle'.")
def mouse_release(button: str = "left") -> str:
    name = (button or "left").strip().lower()
    if get_supported() == "linux":
        from evdev import UInput, ecodes as e
        codes = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}
        code = codes.get(name)
        if code is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        ui.write(e.EV_KEY, code, 0)
        ui.syn()
    else:
        from pynput.mouse import Controller, Button
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
        if btn is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        Controller().release(btn)
    return f"{button} button up"


@tool("Scroll at the cursor's current position. dx and dy are wheel units — "
      "positive dy scrolls up, negative dy scrolls down; dx scrolls horizontally.")
def mouse_scroll(dx: int = 0, dy: int = 0) -> str:
    if get_supported() == "linux":
        from evdev import UInput, ecodes as e
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        if int(dy):
            ui.write(e.EV_REL, e.REL_WHEEL, int(dy))
        if int(dx):
            ui.write(e.EV_REL, e.REL_HWHEEL, int(dx))
        ui.syn()
    else:
        from pynput.mouse import Controller
        Controller().scroll(int(dx), int(dy))
    return f"scrolled ({dx}, {dy})"


@tool("Type a string of text at the focused input. Sends one keystroke per character.")
def keyboard_type(text: str) -> str:
    text = text or ""
    if get_supported() == "linux":
        from evdev import UInput, ecodes as e
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        keymap = keyboard.ascii_keymap()
        for ch in text:
            entry = keymap.get(ch)
            if entry is None:
                raise ValueError(
                    f"non-ASCII character {ch!r} cannot be typed via uinput; "
                    "use clipboard paste for arbitrary unicode"
                )
            keycode, shifted = entry
            if shifted:
                ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
            ui.write(e.EV_KEY, keycode, 1)
            ui.syn()
            ui.write(e.EV_KEY, keycode, 0)
            if shifted:
                ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
            ui.syn()
    else:
        from pynput.keyboard import Controller
        Controller().type(text)
    return f"typed {len(text)} chars"


@tool("Press and release a single key or chord. Examples: 'enter', 'tab', 'esc', "
      "'a', 'f5', 'ctrl+c', 'ctrl+shift+t'. Chord parts are joined with '+'.")
def keyboard_tap(key: str) -> str:
    parts = [p.strip() for p in (key or "").split("+") if p.strip()]
    if not parts:
        raise ValueError("empty key")
    target = get_supported()
    resolved = [keyboard.resolve(target, p) for p in parts]
    if target == "linux":
        from evdev import UInput, ecodes as e
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        for code in resolved[:-1]:
            ui.write(e.EV_KEY, code, 1)
        ui.write(e.EV_KEY, resolved[-1], 1)
        ui.syn()
        ui.write(e.EV_KEY, resolved[-1], 0)
        for code in reversed(resolved[:-1]):
            ui.write(e.EV_KEY, code, 0)
        ui.syn()
    else:
        from pynput.keyboard import Controller
        kb = Controller()
        if len(resolved) == 1:
            kb.tap(resolved[0])
            return f"tapped {key}"
        for k in resolved[:-1]:
            kb.press(k)
        kb.tap(resolved[-1])
        for k in reversed(resolved[:-1]):
            kb.release(k)
    return f"tapped {key}"


@tool("Press a key without releasing it. Pair with keyboard_release. Use for held-modifier "
      "patterns (e.g. shift held while clicking multiple items). key: same syntax as keyboard_tap "
      "(but a single key, not a chord).")
def keyboard_press(key: str) -> str:
    raw = (key or "").strip()
    if not raw:
        raise ValueError("empty key")
    target = get_supported()
    resolved = keyboard.resolve(target, raw)
    if target == "linux":
        from evdev import UInput, ecodes as e
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        ui.write(e.EV_KEY, resolved, 1)
        ui.syn()
    else:
        from pynput.keyboard import Controller
        Controller().press(resolved)
    return f"{key} down"


@tool("Release a previously held key.")
def keyboard_release(key: str) -> str:
    raw = (key or "").strip()
    if not raw:
        raise ValueError("empty key")
    target = get_supported()
    resolved = keyboard.resolve(target, raw)
    if target == "linux":
        from evdev import UInput, ecodes as e
        global uinput_device
        if uinput_device is None:
            uinput_device = UInput({
                e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX)) + [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            }, name="eternego-virtual-input")
            time.sleep(0.1)
        ui = uinput_device
        ui.write(e.EV_KEY, resolved, 0)
        ui.syn()
    else:
        from pynput.keyboard import Controller
        Controller().release(resolved)
    return f"{key} up"


def available() -> bool:
    """True when input verbs can fire on this host.

    Linux: needs /dev/uinput writable AND a session to deliver events to.
    macOS / Windows: probes pynput's controller (Quartz / SendInput) — raises
    on a session that can't accept synthesized input.
    """
    target_os = get_supported()
    if target_os == "linux":
        import os
        if not os.access("/dev/uinput", os.W_OK):
            return False
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    try:
        from pynput.mouse import Controller
        Controller().position
        return True
    except Exception:
        return False
