"""Keyboard — chord-part resolution and ASCII keymap.

Tests the Linux path (evdev) since the test runner is Linux-only and
pynput requires a real display. The pynput branch in keyboard.resolve
is exercised end-to-end via desktop_test.py through the dispatcher.
"""

import platform


def test_resolve_alias_returns_linux_keycode():
    if platform.system() != "Linux": return
    from application.platform import keyboard
    from evdev import ecodes as e
    assert keyboard.resolve("linux","enter") == e.KEY_ENTER
    assert keyboard.resolve("linux","return") == e.KEY_ENTER
    assert keyboard.resolve("linux","ctrl") == e.KEY_LEFTCTRL
    assert keyboard.resolve("linux","control") == e.KEY_LEFTCTRL
    assert keyboard.resolve("linux","shift") == e.KEY_LEFTSHIFT
    assert keyboard.resolve("linux","caps_lock") == e.KEY_CAPSLOCK


def test_resolve_aliases_are_case_insensitive():
    if platform.system() != "Linux": return
    from application.platform import keyboard
    from evdev import ecodes as e
    assert keyboard.resolve("linux","ENTER") == e.KEY_ENTER
    assert keyboard.resolve("linux","Ctrl") == e.KEY_LEFTCTRL


def test_resolve_function_keys():
    if platform.system() != "Linux": return
    from application.platform import keyboard
    from evdev import ecodes as e
    assert keyboard.resolve("linux","f1") == e.KEY_F1
    assert keyboard.resolve("linux","F12") == e.KEY_F12
    assert keyboard.resolve("linux","f24") == e.KEY_F24


def test_resolve_single_ascii_char():
    if platform.system() != "Linux": return
    from application.platform import keyboard
    from evdev import ecodes as e
    assert keyboard.resolve("linux","a") == e.KEY_A
    assert keyboard.resolve("linux","Z") == e.KEY_Z
    assert keyboard.resolve("linux","1") == e.KEY_1


def test_resolve_unknown_key_raises():
    if platform.system() != "Linux": return
    from application.platform import keyboard
    try:
        keyboard.resolve("linux","notakey")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "unknown key" in str(exc)


def test_resolve_function_key_out_of_range_raises():
    if platform.system() != "Linux": return
    from application.platform import keyboard
    try:
        keyboard.resolve("linux","f99")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_ascii_keymap_basic_entries():
    if platform.system() != "Linux": return
    from application.platform import keyboard
    from evdev import ecodes as e
    m = keyboard.ascii_keymap()
    assert m["a"] == (e.KEY_A, False)
    assert m["A"] == (e.KEY_A, True)
    assert m["1"] == (e.KEY_1, False)
    assert m["!"] == (e.KEY_1, True)
    assert m[" "] == (e.KEY_SPACE, False)
    assert m["\n"] == (e.KEY_ENTER, False)


def test_ascii_keymap_punctuation():
    if platform.system() != "Linux": return
    from application.platform import keyboard
    from evdev import ecodes as e
    m = keyboard.ascii_keymap()
    assert m["-"] == (e.KEY_MINUS, False)
    assert m["_"] == (e.KEY_MINUS, True)
    assert m["{"] == (e.KEY_LEFTBRACE, True)
    assert m[":"] == (e.KEY_SEMICOLON, True)
    assert m["?"] == (e.KEY_SLASH, True)
