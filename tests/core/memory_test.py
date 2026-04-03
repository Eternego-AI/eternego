import os
import tempfile
from datetime import datetime

from application.core.brain.data import Signal, SignalEvent, Perception, Meaning
from application.core.brain.mind.memory import Memory
from application.core.data import Model, Persona


class TestMeaning(Meaning):
    name = "Test"
    def description(self): return "A test meaning"
    def clarify(self): return "Please clarify"
    def reply(self): return "Reply prompt"
    def path(self): return "Extract JSON"
    def summarize(self): return "Summarize"


class NoReplyMeaning(Meaning):
    name = "NoReply"
    def description(self): return "Meaning with no reply"
    def clarify(self): return None
    def reply(self): return None
    def path(self): return "Extract JSON"
    def summarize(self): return "Summarize"


class NoPathMeaning(Meaning):
    name = "NoPath"
    def description(self): return "Meaning with no path"
    def clarify(self): return None
    def reply(self): return "Reply prompt"
    def path(self): return None
    def summarize(self): return None


def _persona():
    return Persona(id="test-persona", name="Primus", model=Model(name="llama3"))


def _signal(event=SignalEvent.heard, content="hello", id="s1", ts=None):
    return Signal(id=id, event=event, content=content, created_at=ts or datetime(2026, 3, 15, 10, 0))


_original_home = os.environ.get("HOME")
_tmp_dir = None


def _setup():
    global _tmp_dir
    _tmp_dir = tempfile.mkdtemp()
    os.environ["HOME"] = _tmp_dir


def _teardown():
    if _original_home:
        os.environ["HOME"] = _original_home


def _memory(meanings=None):
    _setup()
    p = _persona()
    return Memory(p, meanings or [TestMeaning(p)])


# ── Trigger and needs_realizing ──────────────────────────────────────────────

def test_trigger_adds_signal():
    mind = _memory()
    s = _signal()
    mind.trigger(s)
    assert len(mind.signals) == 1
    assert mind.signals[0].id == "s1"
    _teardown()


def test_needs_realizing_returns_unattached_heard_signals():
    mind = _memory()
    mind.trigger(_signal(SignalEvent.heard, id="s1"))
    mind.trigger(_signal(SignalEvent.answered, id="s2"))
    unattended = mind.needs_realizing
    assert len(unattended) == 1
    assert unattended[0].id == "s1"
    _teardown()


# ── Realize ──────────────────────────────────────────────────────────────────

def test_realize_creates_perception():
    mind = _memory()
    s = _signal()
    mind.trigger(s)
    mind.realize(s, "greeting")
    assert len(mind.perceptions) == 1
    assert mind.perceptions[0].impression == "greeting"
    assert s in mind.perceptions[0].thread
    _teardown()


def test_realize_appends_to_existing_perception():
    mind = _memory()
    s1 = _signal(id="s1", content="hello")
    s2 = _signal(id="s2", content="how are you")
    mind.trigger(s1)
    mind.trigger(s2)
    mind.realize(s1, "greeting")
    mind.realize(s2, "greeting")
    assert len(mind.perceptions) == 1
    assert len(mind.perceptions[0].thread) == 2
    _teardown()


def test_realize_clears_signal_from_needs_realizing():
    mind = _memory()
    s = _signal()
    mind.trigger(s)
    assert len(mind.needs_realizing) == 1
    mind.realize(s, "greeting")
    assert len(mind.needs_realizing) == 0
    _teardown()


def test_realize_removes_existing_thought_on_heard_signal():
    mind = _memory()
    p = _persona()
    s1 = _signal(id="s1")
    mind.trigger(s1)
    mind.realize(s1, "greeting")
    mind.understand(mind.perceptions[0], TestMeaning(p))
    assert len(mind.intentions) == 1

    s2 = _signal(id="s2", content="actually never mind")
    mind.trigger(s2)
    mind.realize(s2, "greeting")
    assert len(mind.intentions) == 0
    _teardown()


# ── Understand ───────────────────────────────────────────────────────────────

def test_understand_creates_thought():
    mind = _memory()
    p = _persona()
    s = _signal()
    mind.trigger(s)
    mind.realize(s, "greeting")
    thought = mind.understand(mind.perceptions[0], TestMeaning(p))
    assert len(mind.intentions) == 1
    assert thought.meaning.name == "Test"
    assert thought.id != ""
    _teardown()


def test_needs_understanding_returns_perceptions_without_thoughts():
    mind = _memory()
    p = _persona()
    s1 = _signal(id="s1")
    s2 = _signal(id="s2")
    mind.trigger(s1)
    mind.trigger(s2)
    mind.realize(s1, "greeting")
    mind.realize(s2, "question")
    assert len(mind.needs_understanding) == 2

    mind.understand(mind.perceptions[0], TestMeaning(p))
    assert len(mind.needs_understanding) == 1
    _teardown()


# ── Needs recognition / decision / conclusion ────────────────────────────────

def test_needs_recognition_when_last_signal_is_heard():
    mind = _memory()
    p = _persona()
    s = _signal(SignalEvent.heard)
    mind.trigger(s)
    mind.realize(s, "greeting")
    mind.understand(mind.perceptions[0], TestMeaning(p))
    assert len(mind.needs_recognition) == 1
    _teardown()


def test_needs_recognition_empty_when_no_reply():
    mind = _memory()
    p = _persona()
    s = _signal(SignalEvent.heard)
    mind.trigger(s)
    mind.realize(s, "greeting")
    mind.understand(mind.perceptions[0], NoReplyMeaning(p))
    assert len(mind.needs_recognition) == 0
    _teardown()


def test_needs_decision_when_answered_and_has_path():
    mind = _memory()
    p = _persona()
    s = _signal(SignalEvent.heard)
    mind.trigger(s)
    mind.realize(s, "greeting")
    thought = mind.understand(mind.perceptions[0], TestMeaning(p))
    mind.answer(thought, "hi there", SignalEvent.answered)
    assert len(mind.needs_decision) == 1
    _teardown()


def test_needs_decision_when_no_reply_and_has_path():
    mind = _memory()
    p = _persona()
    s = _signal(SignalEvent.heard)
    mind.trigger(s)
    mind.realize(s, "greeting")
    mind.understand(mind.perceptions[0], NoReplyMeaning(p))
    assert len(mind.needs_decision) == 1
    _teardown()


def test_needs_conclusion_when_recap_present():
    mind = _memory()
    p = _persona()
    s = _signal(SignalEvent.heard)
    mind.trigger(s)
    mind.realize(s, "greeting")
    thought = mind.understand(mind.perceptions[0], TestMeaning(p))
    mind.answer(thought, "done", SignalEvent.recap)
    assert len(mind.needs_conclusion) == 1
    _teardown()


# ── Answer and inform ────────────────────────────────────────────────────────

def test_answer_appends_signal_to_thread():
    mind = _memory()
    p = _persona()
    s = _signal()
    mind.trigger(s)
    mind.realize(s, "greeting")
    thought = mind.understand(mind.perceptions[0], TestMeaning(p))
    mind.answer(thought, "hi there", SignalEvent.answered)
    assert len(thought.perception.thread) == 2
    assert thought.perception.thread[-1].content == "hi there"
    assert thought.perception.thread[-1].event == SignalEvent.answered
    _teardown()


def test_inform_appends_tool_result_to_thread():
    mind = _memory()
    p = _persona()
    s = _signal()
    mind.trigger(s)
    mind.realize(s, "greeting")
    thought = mind.understand(mind.perceptions[0], TestMeaning(p))
    tool_signal = Signal(id="tool1", event=SignalEvent.executed, content="result: ok")
    mind.inform(thought, tool_signal)
    assert thought.perception.thread[-1].event == SignalEvent.executed
    assert "result: ok" in thought.perception.thread[-1].content
    _teardown()


# ── Forget ───────────────────────────────────────────────────────────────────

def test_forget_removes_thought_and_exclusive_signals():
    mind = _memory()
    p = _persona()
    s = _signal()
    mind.trigger(s)
    mind.realize(s, "greeting")
    thought = mind.understand(mind.perceptions[0], TestMeaning(p))
    mind.answer(thought, "response", SignalEvent.answered)

    assert len(mind.intentions) == 1
    assert len(mind.signals) == 2

    mind.forget(thought)

    assert len(mind.intentions) == 0
    assert len(mind.perceptions) == 0
    assert len(mind.signals) == 0
    _teardown()


# ── Most important ───────────────────────────────────────────────────────────

def test_most_important_thought_selects_highest_priority():
    mind = _memory()
    p = _persona()
    s1 = _signal(id="s1", ts=datetime(2026, 3, 15, 10, 0))
    s2 = _signal(id="s2", ts=datetime(2026, 3, 15, 10, 1))
    mind.trigger(s1)
    mind.trigger(s2)
    mind.realize(s1, "low")
    mind.realize(s2, "high")
    t1 = mind.understand(mind.perceptions[0], TestMeaning(p), priority=1)
    t2 = mind.understand(mind.perceptions[1], TestMeaning(p), priority=5)

    result = mind.most_important_thought([t1, t2])
    assert result is t2
    _teardown()


def test_most_important_thought_returns_none_for_empty():
    mind = _memory()
    assert mind.most_important_thought([]) is None
    _teardown()


# ── Settled ──────────────────────────────────────────────────────────────────

def test_settled_when_nothing_to_process():
    mind = _memory()
    assert mind.settled is True
    _teardown()


def test_not_settled_when_signals_need_realizing():
    mind = _memory()
    mind.trigger(_signal())
    assert mind.settled is False
    _teardown()


# ── Changed ──────────────────────────────────────────────────────────────────

def test_changed_detects_new_signals():
    mind = _memory()
    assert mind.changed() is False
    mind.trigger(_signal(id="s1"))
    assert mind.changed() is True
    assert mind.changed() is False  # no new signals
    _teardown()


def test_changed_resets_after_signals_realized():
    mind = _memory()
    s = _signal()
    mind.trigger(s)
    mind.changed()  # mark as seen
    mind.realize(s, "greeting")
    assert mind.changed() is False
    _teardown()


# ── Persist and remember roundtrip ───────────────────────────────────────────

def test_persist_and_remember_roundtrip():
    _setup()
    p = _persona()
    meanings = [TestMeaning(p)]
    mind = Memory(p, meanings)

    s = _signal(SignalEvent.heard, "hello", "s1")
    mind.trigger(s)
    mind.realize(s, "greeting")
    mind.understand(mind.perceptions[0], meanings[0], priority=3)
    mind.answer(mind.intentions[0], "hi", SignalEvent.answered)

    mind.persist()

    # Load into fresh memory
    mind2 = Memory(p, meanings)
    mind2.remember()

    assert len(mind2.signals) == 2
    assert len(mind2.perceptions) == 1
    assert mind2.perceptions[0].impression == "greeting"
    assert len(mind2.intentions) == 1
    assert mind2.intentions[0].meaning.name == "Test"
    assert mind2.intentions[0].priority == 3
    _teardown()


# ── Prompts ──────────────────────────────────────────────────────────────────

def test_prompts_builds_messages_from_thread():
    mind = _memory()
    p = _persona()
    s = _signal(SignalEvent.heard, "hello")
    mind.trigger(s)
    mind.realize(s, "greeting")
    thought = mind.understand(mind.perceptions[0], TestMeaning(p))
    mind.answer(thought, "hi there", SignalEvent.answered)

    prompts = mind.prompts(thought)
    assert len(prompts) == 2
    assert prompts[0]["role"] == "user"
    assert prompts[1]["role"] == "assistant"
    _teardown()


def test_prompts_collapses_before_last_summary():
    mind = _memory()
    p = _persona()
    s1 = _signal(SignalEvent.heard, "first question", "s1")
    mind.trigger(s1)
    mind.realize(s1, "topic")
    thought = mind.understand(mind.perceptions[0], TestMeaning(p))
    mind.answer(thought, "first answer", SignalEvent.answered)
    mind.answer(thought, "summary of above", SignalEvent.summarized)

    s2 = _signal(SignalEvent.heard, "second question", "s2")
    mind.trigger(s2)
    mind.realize(s2, "topic")

    prompts = mind.prompts(thought)
    # Should start from the summarized signal, not from the beginning
    assert any("summary of above" in p["content"] for p in prompts)
    _teardown()
