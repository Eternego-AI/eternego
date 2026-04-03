import types

from application.platform.reflections import sorted_by, has_ability


def _make_module():
    mod = types.ModuleType("fake")

    def first():
        pass
    first.stage = True
    first.stage_order = 2

    def second():
        pass
    second.stage = True
    second.stage_order = 1

    def helper():
        pass

    mod.first = first
    mod.second = second
    mod.helper = helper
    return mod


def test_sorted_by_returns_callables_with_attribute():
    mod = _make_module()
    result = sorted_by(mod, "stage")
    names = [name for name, _ in result]
    assert "first" in names
    assert "second" in names
    assert "helper" not in names


def test_sorted_by_respects_order():
    mod = _make_module()
    result = sorted_by(mod, "stage")
    names = [name for name, _ in result]
    assert names.index("second") < names.index("first")


def test_has_ability_returns_true_for_matching():
    mod = _make_module()
    assert has_ability(mod, "first", "stage")


def test_has_ability_returns_false_for_missing_attribute():
    mod = _make_module()
    assert not has_ability(mod, "helper", "stage")


def test_has_ability_returns_false_for_missing_function():
    mod = _make_module()
    assert not has_ability(mod, "nonexistent", "stage")
