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

Positional-argument convention: every mouse action verb takes its target
position as its first two args, named with the `x`/`y` prefix (e.g. `x`,
`y`, `x_from`, `y_from`, `x_to`, `y_to`). Coordinates are compositor
absolute — top-left of the desktop is (0, 0). Each verb writes the
target via the kernel's absolute-pointer interface (EV_ABS on Linux,
pynput's absolute position setter on mac/Windows), so cursor lands
exactly there with no acceleration or relative-motion guesswork. The
screen ability one layer up uses the `x`/`y` prefix to decide which
kwargs to translate from screenshot-pixel space to compositor space.
Non-position kwargs (`button`, `count`, `dx`, `dy` for scroll ticks,
`text`, `key`) must NOT start with `x` or `y` so they pass through
untouched.
"""

import json
import re
import subprocess
import time

from application.platform import keyboard
from application.platform.OS import get_supported


# Two cached uinput devices on Linux. They're created lazily on first use
# of any verb that needs them. Splitting pointer and keyboard into separate
# devices is load-bearing — libinput classifies an EV_ABS+full-keyboard
# device as "weird" and silently drops its absolute pointer events. Keeping
# the pointer device minimal (3 mouse buttons + ABS X/Y + INPUT_PROP_POINTER)
# is what makes the compositor honor absolute placement.
mouse_device = None
keyboard_device = None


def locate_cursor() -> tuple[int, int]:
    """Current cursor position in compositor coords. Queried fresh on every
    call — no cache. macOS uses Quartz, Windows uses GetCursorPos, Linux
    goes through pynput (which reads via XWayland on Wayland sessions)."""
    target_os = get_supported()
    if target_os == "mac":
        from Quartz import NSEvent
        loc = NSEvent.mouseLocation()
        # Quartz origin is bottom-left; flip to top-left.
        from Quartz import CGMainDisplayID, CGDisplayBounds
        screen_h = int(CGDisplayBounds(CGMainDisplayID()).size.height)
        return int(loc.x), int(screen_h - loc.y)
    if target_os == "windows":
        import ctypes
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return int(pt.x), int(pt.y)
    if target_os == "linux":
        from pynput.mouse import Controller
        x, y = Controller().position
        return int(x), int(y)
    raise NotImplementedError(f"locate_cursor not supported on this OS")


def linux_bbox() -> tuple[int, int]:
    """Compositor logical bbox (max_x, max_y) on Linux.

    Used once at pointer-device init to set the EV_ABS axis ranges so the
    compositor maps ABS values 1:1 to compositor coordinates. Tries
    kscreen-doctor first (Plasma Wayland), falls back to xrandr (X11 and
    XWayland), then to (1920, 1080) as a single-monitor floor.
    """
    try:
        data = json.loads(subprocess.check_output(["kscreen-doctor", "-j"], timeout=2))
        mx, my = 0, 0
        for o in data.get("outputs", []):
            if not o.get("enabled"):
                continue
            pos = o.get("pos") or {}
            mid = o.get("currentModeId")
            mode = next((m for m in o.get("modes", []) if m.get("id") == mid), None)
            if not mode:
                continue
            scale = float(o.get("scale") or 1.0)
            mx = max(mx, int(pos.get("x", 0)) + int(int(mode["size"]["width"]) / scale))
            my = max(my, int(pos.get("y", 0)) + int(int(mode["size"]["height"]) / scale))
        if mx and my:
            return mx, my
    except Exception:
        pass
    try:
        out = subprocess.check_output(["xrandr", "--query"], timeout=2).decode()
        m = re.search(r"current\s+(\d+)\s*x\s*(\d+)", out)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return 1920, 1080


def mouse_move(x: int, y: int) -> str:
    if get_supported() == "linux":
        from evdev import UInput, AbsInfo, ecodes as e
        global mouse_device
        if mouse_device is None:
            bw, bh = linux_bbox()
            mouse_device = UInput(
                {
                    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                    e.EV_ABS: [
                        (e.ABS_X, AbsInfo(value=0, min=0, max=bw, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_Y, AbsInfo(value=0, min=0, max=bh, fuzz=0, flat=0, resolution=0)),
                    ],
                    e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL],
                },
                name="eternego-pointer",
                input_props=[e.INPUT_PROP_POINTER],
            )
            time.sleep(0.1)
        ui = mouse_device
        ui.write(e.EV_ABS, e.ABS_X, int(x))
        ui.write(e.EV_ABS, e.ABS_Y, int(y))
        ui.syn()
    else:
        from pynput.mouse import Controller
        Controller().position = (int(x), int(y))
    return f"moved to ({x}, {y})"


def mouse_click(x: int, y: int, button: str = "left", count: int = 1) -> str:
    name = (button or "left").strip().lower()
    if get_supported() == "linux":
        from evdev import UInput, AbsInfo, ecodes as e
        codes = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}
        code = codes.get(name)
        if code is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        global mouse_device
        if mouse_device is None:
            bw, bh = linux_bbox()
            mouse_device = UInput(
                {
                    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                    e.EV_ABS: [
                        (e.ABS_X, AbsInfo(value=0, min=0, max=bw, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_Y, AbsInfo(value=0, min=0, max=bh, fuzz=0, flat=0, resolution=0)),
                    ],
                    e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL],
                },
                name="eternego-pointer",
                input_props=[e.INPUT_PROP_POINTER],
            )
            time.sleep(0.1)
        ui = mouse_device
        ui.write(e.EV_ABS, e.ABS_X, int(x))
        ui.write(e.EV_ABS, e.ABS_Y, int(y))
        ui.syn()
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
        mouse = Controller()
        mouse.position = (int(x), int(y))
        mouse.click(btn, int(count))
    return f"{button} click x{count} at ({x}, {y})"


def mouse_drag(x_from: int, y_from: int, x_to: int, y_to: int, button: str = "left") -> str:
    name = (button or "left").strip().lower()
    if get_supported() == "linux":
        from evdev import UInput, AbsInfo, ecodes as e
        codes = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}
        code = codes.get(name)
        if code is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        global mouse_device
        if mouse_device is None:
            bw, bh = linux_bbox()
            mouse_device = UInput(
                {
                    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                    e.EV_ABS: [
                        (e.ABS_X, AbsInfo(value=0, min=0, max=bw, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_Y, AbsInfo(value=0, min=0, max=bh, fuzz=0, flat=0, resolution=0)),
                    ],
                    e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL],
                },
                name="eternego-pointer",
                input_props=[e.INPUT_PROP_POINTER],
            )
            time.sleep(0.1)
        ui = mouse_device
        ui.write(e.EV_ABS, e.ABS_X, int(x_from))
        ui.write(e.EV_ABS, e.ABS_Y, int(y_from))
        ui.syn()
        ui.write(e.EV_KEY, code, 1)
        ui.syn()
        ui.write(e.EV_ABS, e.ABS_X, int(x_to))
        ui.write(e.EV_ABS, e.ABS_Y, int(y_to))
        ui.syn()
        ui.write(e.EV_KEY, code, 0)
        ui.syn()
    else:
        from pynput.mouse import Controller, Button
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
        if btn is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        mouse = Controller()
        mouse.position = (int(x_from), int(y_from))
        mouse.press(btn)
        mouse.position = (int(x_to), int(y_to))
        mouse.release(btn)
    return f"dragged ({x_from}, {y_from}) → ({x_to}, {y_to}) with {button}"


def mouse_press(x: int, y: int, button: str = "left") -> str:
    name = (button or "left").strip().lower()
    if get_supported() == "linux":
        from evdev import UInput, AbsInfo, ecodes as e
        codes = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}
        code = codes.get(name)
        if code is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        global mouse_device
        if mouse_device is None:
            bw, bh = linux_bbox()
            mouse_device = UInput(
                {
                    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                    e.EV_ABS: [
                        (e.ABS_X, AbsInfo(value=0, min=0, max=bw, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_Y, AbsInfo(value=0, min=0, max=bh, fuzz=0, flat=0, resolution=0)),
                    ],
                    e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL],
                },
                name="eternego-pointer",
                input_props=[e.INPUT_PROP_POINTER],
            )
            time.sleep(0.1)
        ui = mouse_device
        ui.write(e.EV_ABS, e.ABS_X, int(x))
        ui.write(e.EV_ABS, e.ABS_Y, int(y))
        ui.syn()
        ui.write(e.EV_KEY, code, 1)
        ui.syn()
    else:
        from pynput.mouse import Controller, Button
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
        if btn is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        mouse = Controller()
        mouse.position = (int(x), int(y))
        mouse.press(btn)
    return f"{button} button down at ({x}, {y})"


def mouse_release(x: int, y: int, button: str = "left") -> str:
    name = (button or "left").strip().lower()
    if get_supported() == "linux":
        from evdev import UInput, AbsInfo, ecodes as e
        codes = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}
        code = codes.get(name)
        if code is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        global mouse_device
        if mouse_device is None:
            bw, bh = linux_bbox()
            mouse_device = UInput(
                {
                    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                    e.EV_ABS: [
                        (e.ABS_X, AbsInfo(value=0, min=0, max=bw, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_Y, AbsInfo(value=0, min=0, max=bh, fuzz=0, flat=0, resolution=0)),
                    ],
                    e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL],
                },
                name="eternego-pointer",
                input_props=[e.INPUT_PROP_POINTER],
            )
            time.sleep(0.1)
        ui = mouse_device
        ui.write(e.EV_ABS, e.ABS_X, int(x))
        ui.write(e.EV_ABS, e.ABS_Y, int(y))
        ui.syn()
        ui.write(e.EV_KEY, code, 0)
        ui.syn()
    else:
        from pynput.mouse import Controller, Button
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
        if btn is None:
            raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
        mouse = Controller()
        mouse.position = (int(x), int(y))
        mouse.release(btn)
    return f"{button} button up at ({x}, {y})"


def mouse_scroll(x: int, y: int, dx: int = 0, dy: int = 0) -> str:
    if get_supported() == "linux":
        from evdev import UInput, AbsInfo, ecodes as e
        global mouse_device
        if mouse_device is None:
            bw, bh = linux_bbox()
            mouse_device = UInput(
                {
                    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                    e.EV_ABS: [
                        (e.ABS_X, AbsInfo(value=0, min=0, max=bw, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_Y, AbsInfo(value=0, min=0, max=bh, fuzz=0, flat=0, resolution=0)),
                    ],
                    e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL],
                },
                name="eternego-pointer",
                input_props=[e.INPUT_PROP_POINTER],
            )
            time.sleep(0.1)
        ui = mouse_device
        ui.write(e.EV_ABS, e.ABS_X, int(x))
        ui.write(e.EV_ABS, e.ABS_Y, int(y))
        ui.syn()
        if int(dy):
            ui.write(e.EV_REL, e.REL_WHEEL, int(dy))
        if int(dx):
            ui.write(e.EV_REL, e.REL_HWHEEL, int(dx))
        ui.syn()
    else:
        from pynput.mouse import Controller
        mouse = Controller()
        mouse.position = (int(x), int(y))
        mouse.scroll(int(dx), int(dy))
    return f"scrolled ({dx}, {dy}) at ({x}, {y})"


def keyboard_type(text: str) -> str:
    text = text or ""
    if get_supported() == "linux":
        from evdev import UInput, ecodes as e
        global keyboard_device
        if keyboard_device is None:
            keyboard_device = UInput(
                {e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX))},
                name="eternego-keyboard",
            )
            time.sleep(0.1)
        ui = keyboard_device
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


def keyboard_tap(key: str) -> str:
    parts = [p.strip() for p in (key or "").split("+") if p.strip()]
    if not parts:
        raise ValueError("empty key")
    target = get_supported()
    resolved = [keyboard.resolve(target, p) for p in parts]
    if target == "linux":
        from evdev import UInput, ecodes as e
        global keyboard_device
        if keyboard_device is None:
            keyboard_device = UInput(
                {e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX))},
                name="eternego-keyboard",
            )
            time.sleep(0.1)
        ui = keyboard_device
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


def keyboard_press(key: str) -> str:
    raw = (key or "").strip()
    if not raw:
        raise ValueError("empty key")
    target = get_supported()
    resolved = keyboard.resolve(target, raw)
    if target == "linux":
        from evdev import UInput, ecodes as e
        global keyboard_device
        if keyboard_device is None:
            keyboard_device = UInput(
                {e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX))},
                name="eternego-keyboard",
            )
            time.sleep(0.1)
        ui = keyboard_device
        ui.write(e.EV_KEY, resolved, 1)
        ui.syn()
    else:
        from pynput.keyboard import Controller
        Controller().press(resolved)
    return f"{key} down"


def keyboard_release(key: str) -> str:
    raw = (key or "").strip()
    if not raw:
        raise ValueError("empty key")
    target = get_supported()
    resolved = keyboard.resolve(target, raw)
    if target == "linux":
        from evdev import UInput, ecodes as e
        global keyboard_device
        if keyboard_device is None:
            keyboard_device = UInput(
                {e.EV_KEY: list(range(e.KEY_RESERVED + 1, e.KEY_MAX))},
                name="eternego-keyboard",
            )
            time.sleep(0.1)
        ui = keyboard_device
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
