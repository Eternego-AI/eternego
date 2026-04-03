import os
import asyncio
import tempfile

from application.business import routine
from application.core import agents, gateways, paths
from application.core.data import Model, Persona
from application.core.brain.data import Meaning
from application.platform import datetimes, filesystem


_original_home = os.environ.get("HOME")


class FakeWorker:
    def __init__(self):
        self.stopped = False
    def run(self, *args): pass
    def nudge(self): pass


class TestMeaning(Meaning):
    name = "Test"
    def description(self): return "Test"
    def clarify(self): return None
    def reply(self): return "Reply"
    def path(self): return None
    def summarize(self): return None


def _setup():
    tmp = tempfile.mkdtemp()
    os.environ["HOME"] = tmp
    agents._personas.clear()
    gateways._active.clear()


def _teardown():
    if _original_home:
        os.environ["HOME"] = _original_home
    agents._personas.clear()
    gateways._active.clear()


def _persona():
    return Persona(id="test-routine", name="Primus", model=Model(name="llama3"))


def _register_persona(p):
    home = paths.home(p.id)
    home.mkdir(parents=True, exist_ok=True)
    for f in ["person.md", "persona-trait.md", "wishes.md", "struggles.md", "traits.md"]:
        (home / f).touch()
    ego = agents.Ego(p, [TestMeaning(p)], FakeWorker())
    agents._personas[p.id] = ego


def test_trigger_fires_matching_spec():
    _setup()
    p = _persona()
    _register_persona(p)

    current_time = datetimes.now().strftime("%H:%M")
    routines_path = paths.routines(p.id)
    routines_path.parent.mkdir(parents=True, exist_ok=True)
    filesystem.write_json(routines_path, {
        "routines": [
            {"spec": "oversee", "time": current_time},
            {"spec": "oversee", "time": "99:99"},
        ]
    })

    result = asyncio.run(routine.trigger(p))
    assert result.success is True
    assert "oversee" in result.message
    _teardown()


def test_trigger_fires_nothing_when_no_match():
    _setup()
    p = _persona()
    _register_persona(p)

    routines_path = paths.routines(p.id)
    routines_path.parent.mkdir(parents=True, exist_ok=True)
    filesystem.write_json(routines_path, {
        "routines": [{"spec": "oversee", "time": "99:99"}]
    })

    result = asyncio.run(routine.trigger(p))
    assert result.success is True
    assert "none" in result.message
    _teardown()


def test_trigger_succeeds_when_no_routines_file():
    _setup()
    p = _persona()
    _register_persona(p)

    result = asyncio.run(routine.trigger(p))
    assert result.success is True
    assert "none" in result.message
    _teardown()


def test_trigger_skips_unknown_spec():
    _setup()
    p = _persona()
    _register_persona(p)

    current_time = datetimes.now().strftime("%H:%M")
    routines_path = paths.routines(p.id)
    routines_path.parent.mkdir(parents=True, exist_ok=True)
    filesystem.write_json(routines_path, {
        "routines": [{"spec": "nonexistent_function", "time": current_time}]
    })

    result = asyncio.run(routine.trigger(p))
    assert result.success is True
    assert "none" in result.message
    _teardown()
