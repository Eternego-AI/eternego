"""Keyboard — chord-part name → keycode resolution and ASCII typing map.

Single source of truth for the alias names the persona uses (`enter`, `ctrl`,
`caps_lock`, `f5`, etc.) and how each OS renders them as a keycode or pynput
Key. desktop.py's input verbs call these from inside their per-OS branches.

The caller passes the OS as the first argument — keyboard does not
introspect it itself, both to keep the function pure and to avoid an
import-cycle hazard with `OS`.

Imports of the OS-specific backend (evdev / pynput) are lazy inside each
function so this module loads on every OS without dragging the wrong
dependency at module-load time.
"""


def resolve(os: str, part: str):
    """Resolve a chord part to the OS-specific keycode/Key.

    `os` is one of 'linux' / 'mac' / 'windows' (the values OS.get_supported
    returns). `part` is a single ASCII char, an alias name (case-insensitive:
    'enter', 'ctrl', 'caps_lock', etc.), or a function key (`f1`..`f24`).

    Returns:
    - On Linux: an evdev integer keycode.
    - On macOS / Windows: a `pynput.keyboard.Key` enum, or the bare string
      for single ASCII characters.

    Raises ValueError if the part isn't recognized.
    """
    if os == "linux":
        from evdev import ecodes as e
        aliases = {
            "return": e.KEY_ENTER, "enter": e.KEY_ENTER,
            "esc": e.KEY_ESC, "escape": e.KEY_ESC,
            "tab": e.KEY_TAB, "space": e.KEY_SPACE,
            "backspace": e.KEY_BACKSPACE,
            "delete": e.KEY_DELETE, "del": e.KEY_DELETE,
            "up": e.KEY_UP, "down": e.KEY_DOWN,
            "left": e.KEY_LEFT, "right": e.KEY_RIGHT,
            "home": e.KEY_HOME, "end": e.KEY_END,
            "pageup": e.KEY_PAGEUP, "page_up": e.KEY_PAGEUP,
            "pagedown": e.KEY_PAGEDOWN, "page_down": e.KEY_PAGEDOWN,
            "insert": e.KEY_INSERT,
            "ctrl": e.KEY_LEFTCTRL, "control": e.KEY_LEFTCTRL,
            "shift": e.KEY_LEFTSHIFT,
            "alt": e.KEY_LEFTALT, "option": e.KEY_LEFTALT,
            "cmd": e.KEY_LEFTMETA, "command": e.KEY_LEFTMETA,
            "meta": e.KEY_LEFTMETA, "super": e.KEY_LEFTMETA, "win": e.KEY_LEFTMETA,
            "caps_lock": e.KEY_CAPSLOCK, "capslock": e.KEY_CAPSLOCK,
        }
        lowered = part.lower()
        if lowered in aliases:
            return aliases[lowered]
        if len(part) == 1 and part in ascii_keymap():
            return ascii_keymap()[part][0]
        if lowered.startswith("f") and lowered[1:].isdigit() and 1 <= int(lowered[1:]) <= 24:
            return getattr(e, f"KEY_F{int(lowered[1:])}")
        raise ValueError(f"unknown key: {part!r}")

    from pynput.keyboard import Key
    aliases = {
        "return": Key.enter, "enter": Key.enter,
        "esc": Key.esc, "escape": Key.esc,
        "tab": Key.tab, "space": Key.space,
        "backspace": Key.backspace,
        "delete": Key.delete, "del": Key.delete,
        "up": Key.up, "down": Key.down,
        "left": Key.left, "right": Key.right,
        "home": Key.home, "end": Key.end,
        "pageup": Key.page_up, "page_up": Key.page_up,
        "pagedown": Key.page_down, "page_down": Key.page_down,
        **({"insert": Key.insert} if hasattr(Key, "insert") else {}),
        "ctrl": Key.ctrl, "control": Key.ctrl,
        "shift": Key.shift,
        "alt": Key.alt, "option": Key.alt,
        "cmd": Key.cmd, "command": Key.cmd,
        "meta": Key.cmd, "super": Key.cmd, "win": Key.cmd,
        "caps_lock": Key.caps_lock, "capslock": Key.caps_lock,
    }
    lowered = part.lower()
    if lowered in aliases:
        return aliases[lowered]
    if len(part) == 1:
        return part
    if lowered.startswith("f") and lowered[1:].isdigit() and 1 <= int(lowered[1:]) <= 24:
        return getattr(Key, lowered)
    raise ValueError(f"unknown key: {part!r}")


def ascii_keymap() -> dict:
    """ASCII char → (evdev keycode, requires_shift) for keyboard_type on Linux.

    macOS / Windows go through pynput's `Controller.type(text)` which accepts
    the whole string at once, so they never call this function — it's
    Linux-only by design and imports evdev lazily.
    """
    from evdev import ecodes as e

    m = {}
    for ch in "abcdefghijklmnopqrstuvwxyz":
        keycode = getattr(e, f"KEY_{ch.upper()}")
        m[ch] = (keycode, False)
        m[ch.upper()] = (keycode, True)
    for ch in "0123456789":
        m[ch] = (getattr(e, f"KEY_{ch}"), False)
    for digit, shifted in zip("1234567890", "!@#$%^&*()"):
        m[shifted] = (getattr(e, f"KEY_{digit}"), True)

    m[" "] = (e.KEY_SPACE, False)
    m["\n"] = (e.KEY_ENTER, False)
    m["\t"] = (e.KEY_TAB, False)
    m["-"] = (e.KEY_MINUS, False); m["_"] = (e.KEY_MINUS, True)
    m["="] = (e.KEY_EQUAL, False); m["+"] = (e.KEY_EQUAL, True)
    m["["] = (e.KEY_LEFTBRACE, False); m["{"] = (e.KEY_LEFTBRACE, True)
    m["]"] = (e.KEY_RIGHTBRACE, False); m["}"] = (e.KEY_RIGHTBRACE, True)
    m[";"] = (e.KEY_SEMICOLON, False); m[":"] = (e.KEY_SEMICOLON, True)
    m["'"] = (e.KEY_APOSTROPHE, False); m['"'] = (e.KEY_APOSTROPHE, True)
    m[","] = (e.KEY_COMMA, False); m["<"] = (e.KEY_COMMA, True)
    m["."] = (e.KEY_DOT, False); m[">"] = (e.KEY_DOT, True)
    m["/"] = (e.KEY_SLASH, False); m["?"] = (e.KEY_SLASH, True)
    m["\\"] = (e.KEY_BACKSLASH, False); m["|"] = (e.KEY_BACKSLASH, True)
    m["`"] = (e.KEY_GRAVE, False); m["~"] = (e.KEY_GRAVE, True)
    return m
