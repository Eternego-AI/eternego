"""Desktop input — Linux uinput branch.

Each verb is checked by stubbing uinput_device to a recorder and inspecting
the (type, code, value) tuple sequence the verb emits. The pynput branch on
macOS / Windows is not tested here — pynput's own backends need a real display
and the project doesn't currently run those CIs.
"""

import platform


class Recorder:
    """Stand-in for evdev.UInput. Records calls in order."""

    def __init__(self):
        self.events = []
        self.syns = 0

    def write(self, type_code, code, value):
        self.events.append((type_code, code, value))

    def syn(self):
        self.syns += 1
        self.events.append(("SYN", None, None))


def test_mouse_move_emits_slam_then_target():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.mouse_move(100, 200)
    rels = [(c, v) for (t, c, v) in rec.events if t == e.EV_REL]
    assert rels == [(e.REL_X, -10000), (e.REL_Y, -10000), (e.REL_X, 100), (e.REL_Y, 200)], rels


def test_mouse_click_left_default():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.mouse_click()
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.BTN_LEFT, 1), (e.BTN_LEFT, 0)], keys


def test_mouse_click_count_two():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.mouse_click("right", 2)
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.BTN_RIGHT, 1), (e.BTN_RIGHT, 0), (e.BTN_RIGHT, 1), (e.BTN_RIGHT, 0)], keys


def test_mouse_click_unknown_button_raises():
    if platform.system() != "Linux": return
    from application.platform import desktop
    rec = Recorder()
    desktop.uinput_device = rec
    try:
        desktop.mouse_click("middlex")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_mouse_press_and_release():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.mouse_press("middle")
    desktop.mouse_release("middle")
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.BTN_MIDDLE, 1), (e.BTN_MIDDLE, 0)], keys


def test_mouse_drag_emits_press_move_release():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.mouse_drag(10, 20, 30, 50)
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.BTN_LEFT, 1), (e.BTN_LEFT, 0)], keys
    rels = [(c, v) for (t, c, v) in rec.events if t == e.EV_REL]
    assert (e.REL_X, 30 - 10) in rels and (e.REL_Y, 50 - 20) in rels, rels


def test_mouse_scroll_vertical():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.mouse_scroll(dy=3)
    rels = [(c, v) for (t, c, v) in rec.events if t == e.EV_REL]
    assert rels == [(e.REL_WHEEL, 3)], rels


def test_mouse_scroll_horizontal_and_vertical():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.mouse_scroll(dx=2, dy=-1)
    rels = [(c, v) for (t, c, v) in rec.events if t == e.EV_REL]
    assert (e.REL_WHEEL, -1) in rels and (e.REL_HWHEEL, 2) in rels, rels


def test_keyboard_type_ascii_lower_and_upper():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.keyboard_type("aB")
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    # 'a' → KEY_A press/release; 'B' → SHIFT down, KEY_B press/release, SHIFT up
    assert keys == [
        (e.KEY_A, 1), (e.KEY_A, 0),
        (e.KEY_LEFTSHIFT, 1), (e.KEY_B, 1), (e.KEY_B, 0), (e.KEY_LEFTSHIFT, 0),
    ], keys


def test_keyboard_type_rejects_non_ascii():
    if platform.system() != "Linux": return
    from application.platform import desktop
    rec = Recorder()
    desktop.uinput_device = rec
    try:
        desktop.keyboard_type("é")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "non-ASCII" in str(exc)


def test_keyboard_tap_chord():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.keyboard_tap("ctrl+c")
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    # ctrl down, c down, c up, ctrl up
    assert keys == [
        (e.KEY_LEFTCTRL, 1), (e.KEY_C, 1), (e.KEY_C, 0), (e.KEY_LEFTCTRL, 0),
    ], keys


def test_keyboard_tap_single_key():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.keyboard_tap("enter")
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.KEY_ENTER, 1), (e.KEY_ENTER, 0)], keys


def test_keyboard_press_and_release():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.uinput_device = rec
    desktop.keyboard_press("shift")
    desktop.keyboard_release("shift")
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.KEY_LEFTSHIFT, 1), (e.KEY_LEFTSHIFT, 0)], keys


def test_keyboard_tap_unknown_key_raises():
    if platform.system() != "Linux": return
    from application.platform import desktop
    rec = Recorder()
    desktop.uinput_device = rec
    try:
        desktop.keyboard_tap("notakey")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_available_returns_false_when_uinput_unwritable():
    """available() short-circuits on inaccessible /dev/uinput regardless of session."""
    if platform.system() != "Linux": return
    import os
    from application.platform import desktop
    real_access = os.access
    try:
        os.access = lambda path, mode: False if path == "/dev/uinput" else real_access(path, mode)
        assert desktop.available() is False
    finally:
        os.access = real_access
