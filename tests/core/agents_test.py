import os
import tempfile
from datetime import datetime

from application.core import agents, paths
from application.core.brain.data import Signal, SignalEvent, Meaning
from application.core.data import Model, Persona


class FakeWorker:
    def __init__(self):
        self.stopped = False
        self.nudged = 0

    def run(self, *args):
        pass

    def nudge(self):
        self.nudged += 1


class TestMeaning(Meaning):
    name = "Test"
    def description(self): return "A test meaning"
    def clarify(self): return None
    def reply(self): return "Reply"
    def path(self): return None
    def summarize(self): return None


_original_home = os.environ.get("HOME")


def _setup():
    tmp = tempfile.mkdtemp()
    os.environ["HOME"] = tmp
    return tmp


def _teardown():
    if _original_home:
        os.environ["HOME"] = _original_home
    agents._personas.clear()


def _persona():
    return Persona(id="test-ego", name="Primus", model=Model(name="llama3"))


def _ego(persona=None):
    p = persona or _persona()
    return agents.Ego(p, [TestMeaning(p)], FakeWorker())


# ── Ego construction ─────────────────────────────────────────────────────────

def test_ego_initializes_with_persona_and_memory():
    _setup()
    p = _persona()
    ego = _ego(p)
    assert ego.persona is p
    assert ego.memory is not None
    assert ego.meanings[0].name == "Test"
    _teardown()


# ── Pipeline ─────────────────────────────────────────────────────────────────

def test_consciousness_returns_five_callables():
    _setup()
    ego = _ego()
    consciousness = ego.consciousness()
    assert len(consciousness) == 5
    assert all(callable(step) for step in consciousness)
    _teardown()


# ── Trigger ──────────────────────────────────────────────────────────────────

def test_trigger_adds_signal_to_memory_and_nudges():
    _setup()
    ego = _ego()
    s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
    ego.trigger(s)
    assert len(ego.memory.signals) == 1
    assert ego.worker.nudged == 1
    _teardown()


def test_trigger_ignores_signal_when_worker_stopped():
    _setup()
    ego = _ego()
    ego.worker.stopped = True
    s = Signal(id="s1", event=SignalEvent.heard, content="hello", created_at=datetime(2026, 3, 15, 10, 0))
    ego.trigger(s)
    assert len(ego.memory.signals) == 0
    _teardown()


# ── Incept ───────────────────────────────────────────────────────────────────

def test_incept_injects_perception_and_nudges():
    from application.core.brain.data import Perception
    _setup()
    ego = _ego()
    s = Signal(id="s1", event=SignalEvent.nudged, content="wake up", created_at=datetime(2026, 3, 15, 10, 0))
    p = Perception(impression="wake notification", thread=[s])
    ego.incept(p)
    assert len(ego.memory.perceptions) == 1
    assert ego.memory.perceptions[0].impression == "wake notification"
    assert ego.worker.nudged == 1
    _teardown()


# ── Read ─────────────────────────────────────────────────────────────────────

def test_read_returns_signals_sorted_by_time():
    _setup()
    ego = _ego()
    s1 = Signal(id="s1", event=SignalEvent.heard, content="second", created_at=datetime(2026, 3, 15, 10, 1))
    s2 = Signal(id="s2", event=SignalEvent.heard, content="first", created_at=datetime(2026, 3, 15, 10, 0))
    ego.memory.trigger(s1)
    ego.memory.trigger(s2)
    result = ego.read()
    assert result[0].id == "s2"
    assert result[1].id == "s1"
    _teardown()


# ── Register and find ────────────────────────────────────────────────────────

def test_register_stores_ego_and_find_retrieves_persona():
    _setup()
    p = _persona()
    ego = _ego(p)
    agents.register(p, ego)
    found = agents.find(p.id)
    assert found.id == p.id
    _teardown()


def test_find_raises_when_not_registered():
    _setup()
    try:
        agents.find("nonexistent")
        assert False, "should have raised"
    except agents.MindError:
        pass
    _teardown()


def test_persona_returns_ego():
    _setup()
    p = _persona()
    ego = _ego(p)
    agents.register(p, ego)
    assert agents.persona(p) is ego
    _teardown()


# ── Unload ───────────────────────────────────────────────────────────────────

def test_unload_persists_memory_and_unregisters():
    _setup()
    p = _persona()
    ego = _ego(p)
    agents.register(p, ego)
    ego.unload()

    try:
        agents.find(p.id)
        assert False, "should have raised"
    except agents.MindError:
        pass

    # Memory file should exist
    assert paths.mind_state(p.id).exists()
    _teardown()


# ── Pairing codes ────────────────────────────────────────────────────────────

def test_pair_generates_code_and_take_code_claims_it():
    from application.core.data import Channel
    _setup()
    p = _persona()
    ego = _ego(p)
    agents.register(p, ego)
    channel = Channel(type="telegram", name="12345")
    code = agents.pair(p, channel)

    assert len(code) == 6
    found_persona, ch_type, ch_name = agents.take_code(code)
    assert found_persona.id == p.id
    assert ch_type == "telegram"
    assert ch_name == "12345"
    _teardown()


def test_take_code_raises_on_invalid_code():
    _setup()
    try:
        agents.take_code("INVALID")
        assert False, "should have raised"
    except agents.AgentError:
        pass
    _teardown()


# ── Identity ─────────────────────────────────────────────────────────────────

def test_identity_includes_character():
    _setup()
    p = _persona()
    ego = _ego(p)

    home = paths.home(p.id)
    home.mkdir(parents=True, exist_ok=True)
    (home / "person.md").write_text("")
    (home / "persona-trait.md").write_text("")
    (home / "wishes.md").write_text("")
    (home / "struggles.md").write_text("")
    (home / "traits.md").write_text("")

    result = ego.identity()
    assert "Primus" in result
    assert "# Who You Are" in result
    _teardown()
