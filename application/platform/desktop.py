"""Desktop — keyboard and mouse input primitives.

Wraps `pynput`. Each tool is one thing a person at a keyboard or mouse
does — the verbs the `screen` ability dispatches to. Composition (drag,
chord taps, click-and-screenshot) lives one layer up.

Screen capture lives in `OS.screenshot` — it's a system operation, not
an input verb, so the abilities call it directly rather than through here.

Cross-platform via pynput's own backends: X11 on Linux, Quartz on macOS,
SendInput on Windows. Wayland sessions are not supported by pynput; run
through Docker (X11 inside) on Wayland hosts.

pynput imports are lazy inside each function — instantiating its
backends probes the display, which would crash at module-load time on
headless hosts.
"""

from application.platform.tool import tool


@tool("Move the mouse cursor to absolute screen coordinates (x, y in pixels). "
      "Use the screenshot's pixel space — top-left is (0, 0).")
def mouse_move(x: int, y: int) -> str:
    from pynput.mouse import Controller
    Controller().position = (int(x), int(y))
    return f"moved to ({x}, {y})"


@tool("Click the mouse at the cursor's current position. button is 'left', 'right', or 'middle' "
      "(default 'left'). count is 1 for single click, 2 for double-click.")
def mouse_click(button: str = "left", count: int = 1) -> str:
    from pynput.mouse import Controller, Button
    name = (button or "left").strip().lower()
    btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
    if btn is None:
        raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
    Controller().click(btn, int(count))
    return f"{button} click x{count}"


@tool("Drag the mouse from (from_x, from_y) to (to_x, to_y) while holding a button. "
      "button is 'left', 'right', or 'middle' (default 'left').")
def mouse_drag(from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> str:
    from pynput.mouse import Controller, Button
    name = (button or "left").strip().lower()
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
    from pynput.mouse import Controller, Button
    name = (button or "left").strip().lower()
    btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
    if btn is None:
        raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
    Controller().press(btn)
    return f"{button} button down"


@tool("Release a previously held mouse button. button: 'left', 'right', 'middle'.")
def mouse_release(button: str = "left") -> str:
    from pynput.mouse import Controller, Button
    name = (button or "left").strip().lower()
    btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(name)
    if btn is None:
        raise ValueError(f"unknown mouse button: {button!r}; expected left, right, or middle")
    Controller().release(btn)
    return f"{button} button up"


@tool("Scroll at the cursor's current position. dx and dy are wheel units — "
      "positive dy scrolls up, negative dy scrolls down; dx scrolls horizontally.")
def mouse_scroll(dx: int = 0, dy: int = 0) -> str:
    from pynput.mouse import Controller
    Controller().scroll(int(dx), int(dy))
    return f"scrolled ({dx}, {dy})"


@tool("Type a string of text at the focused input. Sends one keystroke per character.")
def keyboard_type(text: str) -> str:
    from pynput.keyboard import Controller
    Controller().type(text or "")
    return f"typed {len(text or '')} chars"


@tool("Press and release a single key or chord. Examples: 'enter', 'tab', 'esc', "
      "'a', 'f5', 'ctrl+c', 'ctrl+shift+t'. Chord parts are joined with '+'.")
def keyboard_tap(key: str) -> str:
    from pynput.keyboard import Controller, Key
    parts = [p.strip() for p in (key or "").split("+") if p.strip()]
    if not parts:
        raise ValueError("empty key")
    aliases = {
        "return": Key.enter, "enter": Key.enter,
        "esc": Key.esc, "escape": Key.esc,
        "tab": Key.tab, "space": Key.space,
        "backspace": Key.backspace, "delete": Key.delete, "del": Key.delete,
        "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
        "home": Key.home, "end": Key.end,
        "pageup": Key.page_up, "page_up": Key.page_up,
        "pagedown": Key.page_down, "page_down": Key.page_down,
        "insert": Key.insert,
        "ctrl": Key.ctrl, "control": Key.ctrl,
        "shift": Key.shift, "alt": Key.alt, "option": Key.alt,
        "cmd": Key.cmd, "command": Key.cmd, "meta": Key.cmd, "super": Key.cmd, "win": Key.cmd,
        "caps_lock": Key.caps_lock, "capslock": Key.caps_lock,
    }
    resolved = []
    for p in parts:
        if len(p) == 1:
            resolved.append(p)
            continue
        lowered = p.lower()
        if lowered in aliases:
            resolved.append(aliases[lowered])
            continue
        if lowered.startswith("f") and lowered[1:].isdigit() and 1 <= int(lowered[1:]) <= 24:
            resolved.append(getattr(Key, lowered))
            continue
        raise ValueError(f"unknown key: {p!r}")
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
    from pynput.keyboard import Controller, Key
    raw = (key or "").strip()
    if not raw:
        raise ValueError("empty key")
    if len(raw) == 1:
        resolved = raw
    else:
        lowered = raw.lower()
        aliases = {
            "return": Key.enter, "enter": Key.enter,
            "esc": Key.esc, "escape": Key.esc,
            "tab": Key.tab, "space": Key.space,
            "backspace": Key.backspace, "delete": Key.delete, "del": Key.delete,
            "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
            "home": Key.home, "end": Key.end,
            "pageup": Key.page_up, "page_up": Key.page_up,
            "pagedown": Key.page_down, "page_down": Key.page_down,
            "insert": Key.insert,
            "ctrl": Key.ctrl, "control": Key.ctrl,
            "shift": Key.shift, "alt": Key.alt, "option": Key.alt,
            "cmd": Key.cmd, "command": Key.cmd, "meta": Key.cmd, "super": Key.cmd, "win": Key.cmd,
            "caps_lock": Key.caps_lock, "capslock": Key.caps_lock,
        }
        if lowered in aliases:
            resolved = aliases[lowered]
        elif lowered.startswith("f") and lowered[1:].isdigit() and 1 <= int(lowered[1:]) <= 24:
            resolved = getattr(Key, lowered)
        else:
            raise ValueError(f"unknown key: {key!r}")
    Controller().press(resolved)
    return f"{key} down"


@tool("Release a previously held key.")
def keyboard_release(key: str) -> str:
    from pynput.keyboard import Controller, Key
    raw = (key or "").strip()
    if not raw:
        raise ValueError("empty key")
    if len(raw) == 1:
        resolved = raw
    else:
        lowered = raw.lower()
        aliases = {
            "return": Key.enter, "enter": Key.enter,
            "esc": Key.esc, "escape": Key.esc,
            "tab": Key.tab, "space": Key.space,
            "backspace": Key.backspace, "delete": Key.delete, "del": Key.delete,
            "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
            "home": Key.home, "end": Key.end,
            "pageup": Key.page_up, "page_up": Key.page_up,
            "pagedown": Key.page_down, "page_down": Key.page_down,
            "insert": Key.insert,
            "ctrl": Key.ctrl, "control": Key.ctrl,
            "shift": Key.shift, "alt": Key.alt, "option": Key.alt,
            "cmd": Key.cmd, "command": Key.cmd, "meta": Key.cmd, "super": Key.cmd, "win": Key.cmd,
            "caps_lock": Key.caps_lock, "capslock": Key.caps_lock,
        }
        if lowered in aliases:
            resolved = aliases[lowered]
        elif lowered.startswith("f") and lowered[1:].isdigit() and 1 <= int(lowered[1:]) <= 24:
            resolved = getattr(Key, lowered)
        else:
            raise ValueError(f"unknown key: {key!r}")
    Controller().release(resolved)
    return f"{key} up"


def available() -> bool:
    """True when pynput can talk to the display (X session, Quartz, or Win32 input).

    Used by the abilities that gate on screen access. Probes by instantiating
    pynput's mouse Controller — it raises on a headless session."""
    try:
        from pynput.mouse import Controller
        Controller().position
        return True
    except Exception:
        return False
