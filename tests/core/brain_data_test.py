from application.core.brain.data import Signal, SignalEvent, Perception, Thought, Meaning


def test_it_creates_signals_with_defaults():
    s = Signal(id="s1", event=SignalEvent.heard, content="hello")
    assert s.id == "s1"
    assert s.event == SignalEvent.heard
    assert s.content == "hello"
    assert s.channel_type == ""
    assert s.created_at is not None


def test_it_creates_perception_with_empty_thread():
    p = Perception(impression="greeting")
    assert p.impression == "greeting"
    assert p.thread == []


def test_it_creates_perception_with_signals():
    s1 = Signal(id="s1", event=SignalEvent.heard, content="hi")
    s2 = Signal(id="s2", event=SignalEvent.answered, content="hello")
    p = Perception(impression="greeting", thread=[s1, s2])
    assert len(p.thread) == 2


def test_it_generates_thought_id_from_perception():
    p = Perception(impression="test topic", thread=[])

    class TestMeaning(Meaning):
        name = "Test"
        def description(self): return ""
        def clarify(self): return None
        def reply(self): return None
        def path(self): return None
        def summarize(self): return None

    t = Thought(perception=p, meaning=TestMeaning(persona=None))
    assert len(t.id) == 12
    assert t.id != ""


def test_it_generates_consistent_thought_ids():
    p = Perception(impression="same topic", thread=[])

    class TestMeaning(Meaning):
        name = "Test"
        def description(self): return ""
        def clarify(self): return None
        def reply(self): return None
        def path(self): return None
        def summarize(self): return None

    t1 = Thought(perception=p, meaning=TestMeaning(persona=None))
    t2 = Thought(perception=p, meaning=TestMeaning(persona=None))
    assert t1.id == t2.id


def test_it_signal_events_are_strings():
    assert str(SignalEvent.heard) == "heard"
    assert str(SignalEvent.answered) == "answered"
