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


def test_mouse_move_emits_absolute_target():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    desktop.mouse_move(100, 200)
    abss = [(c, v) for (t, c, v) in rec.events if t == e.EV_ABS]
    assert abss == [(e.ABS_X, 100), (e.ABS_Y, 200)], abss


def test_mouse_click_left_default():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    desktop.mouse_click(50, 60)
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.BTN_LEFT, 1), (e.BTN_LEFT, 0)], keys
    abss = [(c, v) for (t, c, v) in rec.events if t == e.EV_ABS]
    assert (e.ABS_X, 50) in abss and (e.ABS_Y, 60) in abss, abss


def test_mouse_click_count_two():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    desktop.mouse_click(0, 0, "right", 2)
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.BTN_RIGHT, 1), (e.BTN_RIGHT, 0), (e.BTN_RIGHT, 1), (e.BTN_RIGHT, 0)], keys


def test_mouse_click_unknown_button_raises():
    if platform.system() != "Linux": return
    from application.platform import desktop
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    try:
        desktop.mouse_click(0, 0, "middlex")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_mouse_press_and_release():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    desktop.mouse_press(10, 20, "middle")
    desktop.mouse_release(30, 40, "middle")
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.BTN_MIDDLE, 1), (e.BTN_MIDDLE, 0)], keys
    abss = [(c, v) for (t, c, v) in rec.events if t == e.EV_ABS]
    assert (e.ABS_X, 10) in abss and (e.ABS_Y, 20) in abss, abss
    assert (e.ABS_X, 30) in abss and (e.ABS_Y, 40) in abss, abss


def test_mouse_drag_emits_press_move_release():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    desktop.mouse_drag(10, 20, 30, 50)
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.BTN_LEFT, 1), (e.BTN_LEFT, 0)], keys
    abss = [(c, v) for (t, c, v) in rec.events if t == e.EV_ABS]
    assert (e.ABS_X, 10) in abss and (e.ABS_Y, 20) in abss, abss
    assert (e.ABS_X, 30) in abss and (e.ABS_Y, 50) in abss, abss


def test_mouse_scroll_vertical():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    desktop.mouse_scroll(70, 80, dy=3)
    abss = [(c, v) for (t, c, v) in rec.events if t == e.EV_ABS]
    assert (e.ABS_X, 70) in abss and (e.ABS_Y, 80) in abss, abss
    rels = [(c, v) for (t, c, v) in rec.events if t == e.EV_REL]
    assert (e.REL_WHEEL, 3) in rels, rels


def test_mouse_scroll_horizontal_and_vertical():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    desktop.mouse_scroll(0, 0, dx=2, dy=-1)
    rels = [(c, v) for (t, c, v) in rec.events if t == e.EV_REL]
    assert (e.REL_WHEEL, -1) in rels and (e.REL_HWHEEL, 2) in rels, rels


def test_keyboard_type_ascii_lower_and_upper():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
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
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
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
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
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
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    desktop.keyboard_tap("enter")
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.KEY_ENTER, 1), (e.KEY_ENTER, 0)], keys


def test_keyboard_press_and_release():
    if platform.system() != "Linux": return
    from application.platform import desktop
    from evdev import ecodes as e
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
    desktop.keyboard_press("shift")
    desktop.keyboard_release("shift")
    keys = [(c, v) for (t, c, v) in rec.events if t == e.EV_KEY]
    assert keys == [(e.KEY_LEFTSHIFT, 1), (e.KEY_LEFTSHIFT, 0)], keys


def test_keyboard_tap_unknown_key_raises():
    if platform.system() != "Linux": return
    from application.platform import desktop
    rec = Recorder()
    desktop.mouse_device = rec
    desktop.keyboard_device = rec
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
