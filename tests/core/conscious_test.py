import os
import json
import tempfile
from datetime import datetime

from application.core.brain.mind import conscious
from application.core.brain.mind.memory import Memory
from application.core.brain.data import Signal, SignalEvent, Meaning
from application.core.data import Model, Persona
from application.platform import ollama


# ── Helpers ──────────────────────────────────────────────────────────────────

class TestMeaning(Meaning):
    name = "Test"
    def description(self): return "A test meaning"
    def clarify(self): return "Please clarify"
    def reply(self): return "Reply prompt"
    def path(self): return "Extract JSON"
    def summarize(self): return "Summarize the result"


class NoPathMeaning(Meaning):
    name = "NoPath"
    def description(self): return "No path meaning"
    def clarify(self): return None
    def reply(self): return "Reply prompt"
    def path(self): return None
    def summarize(self): return None


class NoSummaryMeaning(Meaning):
    name = "NoSummary"
    def description(self): return "No summary meaning"
    def clarify(self): return None
    def reply(self): return "Reply"
    def path(self): return "Extract"
    def summarize(self): return None


class EscalationMeaning(Meaning):
    name = "Escalation"
    def description(self): return "Escalation"
    def clarify(self): return None
    def reply(self): return "I'll figure this out"
    def path(self): return None
    def summarize(self): return None


_original_home = os.environ.get("HOME")


def _setup():
    tmp = tempfile.mkdtemp()
    os.environ["HOME"] = tmp


def _teardown():
    if _original_home:
        os.environ["HOME"] = _original_home


def _persona():
    return Persona(id="test-conscious", name="Primus", model=Model(name="llama3"))


def _signal(id="s1", event=SignalEvent.heard, content="hello", ts=None):
    return Signal(id=id, event=event, content=content, created_at=ts or datetime(2026, 3, 15, 10, 0))


def _memory(meanings=None):
    p = _persona()
    if meanings is None:
        meanings = [TestMeaning(p)]
    return Memory(p, meanings)


def _identity():
    return "You are Primus."


async def _noop_say(text):
    pass


async def _noop_escalate(thread_text, meanings):
    return None


def _stream_json(obj):
    """Convert a dict to ollama streaming format — one chunk per character of JSON."""
    text = json.dumps(obj)
    return [{"message": {"content": c}} for c in text]


# ── Realize ──────────────────────────────────────────────────────────────────

def test_realize_does_nothing_when_no_signals():
    _setup()
    memory = _memory()
    import asyncio
    asyncio.run(conscious.realize(memory, _persona(), _identity))
    assert len(memory.perceptions) == 0
    _teardown()


def test_realize_routes_signal_to_new_impression():
    _setup()
    memory = _memory()
    memory.trigger(_signal())

    ollama.assert_call(
        run=lambda: conscious.realize(memory, _persona(), _identity),
        response=_stream_json({"routes": [{"signal": 1, "threads": [], "new_impressions": ["greeting"]}]}),
    )

    assert len(memory.perceptions) == 1
    assert memory.perceptions[0].impression == "greeting"
    assert len(memory.needs_realizing) == 0
    _teardown()


def test_realize_routes_signal_to_existing_thread():
    _setup()
    memory = _memory()
    s1 = _signal(id="s1", content="hi")
    memory.trigger(s1)
    memory.realize(s1, "greeting")

    s2 = _signal(id="s2", content="how are you")
    memory.trigger(s2)

    ollama.assert_call(
        run=lambda: conscious.realize(memory, _persona(), _identity),
        response=_stream_json({"routes": [{"signal": 1, "threads": [1], "new_impressions": []}]}),
    )

    assert len(memory.perceptions) == 1
    assert len(memory.perceptions[0].thread) == 2
    _teardown()


def test_realize_routes_signal_to_both_existing_and_new():
    _setup()
    memory = _memory()
    s1 = _signal(id="s1", content="existing topic")
    memory.trigger(s1)
    memory.realize(s1, "topic A")

    s2 = _signal(id="s2", content="mixed message")
    memory.trigger(s2)

    ollama.assert_call(
        run=lambda: conscious.realize(memory, _persona(), _identity),
        response=_stream_json({"routes": [{"signal": 1, "threads": [1], "new_impressions": ["topic B"]}]}),
    )

    assert len(memory.perceptions) == 2
    impressions = [p.impression for p in memory.perceptions]
    assert "topic A" in impressions
    assert "topic B" in impressions
    _teardown()


def test_realize_skips_invalid_signal_number():
    _setup()
    memory = _memory()
    memory.trigger(_signal())

    ollama.assert_call(
        run=lambda: conscious.realize(memory, _persona(), _identity),
        response=_stream_json({"routes": [{"signal": 999, "threads": [], "new_impressions": ["x"]}]}),
    )

    assert len(memory.needs_realizing) == 1
    _teardown()


# ── Understand ───────────────────────────────────────────────────────────────

def test_understand_does_nothing_when_no_perceptions():
    _setup()
    memory = _memory()
    import asyncio
    asyncio.run(conscious.understand(memory, _persona(), [TestMeaning(_persona())], _identity, _noop_escalate))
    assert len(memory.intentions) == 0
    _teardown()


def test_understand_picks_meaning_by_row():
    _setup()
    p = _persona()
    meanings = [TestMeaning(p), EscalationMeaning(p)]
    memory = _memory(meanings)
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "greeting")

    ollama.assert_call(
        run=lambda: conscious.understand(memory, p, meanings, _identity, _noop_escalate),
        response=_stream_json({"meaning_row": 1}),
    )

    assert len(memory.intentions) == 1
    assert memory.intentions[0].meaning.name == "Test"
    _teardown()


def test_understand_falls_to_escalation_on_invalid_row():
    _setup()
    p = _persona()
    meanings = [TestMeaning(p), EscalationMeaning(p)]
    memory = _memory(meanings)
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "unknown topic")

    ollama.assert_call(
        run=lambda: conscious.understand(memory, p, meanings, _identity, _noop_escalate),
        response=_stream_json({"meaning_row": 99}),
    )

    assert len(memory.intentions) == 1
    assert memory.intentions[0].meaning.name == "Escalation"
    _teardown()


def test_understand_escalation_with_no_code_uses_escalation_meaning():
    _setup()
    p = _persona()
    meanings = [TestMeaning(p), EscalationMeaning(p)]
    memory = _memory(meanings)
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "unknown")

    ollama.assert_call(
        run=lambda: conscious.understand(memory, p, meanings, _identity, _noop_escalate),
        response=_stream_json({"meaning_row": 2}),
    )

    assert memory.intentions[0].meaning.name == "Escalation"
    _teardown()


# ── Recognize ────────────────────────────────────────────────────────────────

def test_recognize_does_nothing_when_no_thoughts():
    _setup()
    memory = _memory()
    import asyncio
    asyncio.run(conscious.recognize(memory, _persona(), _identity, _noop_say))
    _teardown()


def test_recognize_replies_on_heard_signal():
    _setup()
    p = _persona()
    memory = _memory()
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "greeting")
    memory.understand(memory.perceptions[0], TestMeaning(p))

    said = []

    async def capture_say(text):
        said.append(text)

    ollama.assert_call(
        run=lambda: conscious.recognize(memory, p, _identity, capture_say),
        response={"message": {"content": "Hello there!"}},
    )

    assert said == ["Hello there!"]
    last = memory.intentions[0].perception.thread[-1]
    assert last.event == SignalEvent.answered
    assert last.content == "Hello there!"
    _teardown()


def test_recognize_uses_clarify_after_executed_signal():
    _setup()
    p = _persona()
    memory = _memory()
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "task")
    thought = memory.understand(memory.perceptions[0], TestMeaning(p))
    memory.inform(thought, Signal(id="exec1", event=SignalEvent.executed, content="Error: failed"))

    ollama.assert_call(
        run=lambda: conscious.recognize(memory, p, _identity, _noop_say),
        response={"message": {"content": "Let me try again"}},
    )

    last = thought.perception.thread[-1]
    assert last.event == SignalEvent.clarified
    _teardown()


def test_recognize_forgets_thought_when_no_path():
    _setup()
    p = _persona()
    memory = _memory()
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "greeting")
    memory.understand(memory.perceptions[0], NoPathMeaning(p))

    ollama.assert_call(
        run=lambda: conscious.recognize(memory, p, _identity, _noop_say),
        response={"message": {"content": "Hi!"}},
    )

    assert len(memory.intentions) == 0
    _teardown()


# ── Decide ───────────────────────────────────────────────────────────────────

def test_decide_does_nothing_when_no_thoughts():
    _setup()
    memory = _memory()
    import asyncio
    asyncio.run(conscious.decide(memory, _persona(), _identity))
    _teardown()


def test_decide_creates_recap_when_only_recap_returned():
    _setup()
    p = _persona()
    memory = _memory()
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "task")
    thought = memory.understand(memory.perceptions[0], TestMeaning(p))
    memory.answer(thought, "acknowledged", SignalEvent.answered)

    ollama.assert_call(
        run=lambda: conscious.decide(memory, p, _identity),
        response=_stream_json({"recap": "Already done"}),
    )

    last = thought.perception.thread[-1]
    assert last.event == SignalEvent.recap
    assert last.content == "Already done"
    _teardown()


def test_decide_runs_action_and_informs_with_output():
    _setup()
    p = _persona()

    class ActionMeaning(Meaning):
        name = "Action"
        def description(self): return "Action meaning"
        def clarify(self): return None
        def reply(self): return None
        def path(self): return "Extract tool call"
        def summarize(self): return "Done"
        async def run(self, persona_response):
            async def action():
                return "command output"
            return action

    memory = _memory([ActionMeaning(p)])
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "task")
    memory.understand(memory.perceptions[0], ActionMeaning(p))

    ollama.assert_call(
        run=lambda: conscious.decide(memory, p, _identity),
        response=_stream_json({"tool": "shell.run", "command": "ls", "recap": "Running ls"}),
    )

    events = [s.event for s in memory.intentions[0].perception.thread]
    assert SignalEvent.decided in events
    assert SignalEvent.executed in events
    executed = [s for s in memory.intentions[0].perception.thread if s.event == SignalEvent.executed][0]
    assert "command output" in executed.content
    _teardown()


def test_decide_informs_error_when_run_raises():
    _setup()
    p = _persona()

    class BrokenMeaning(Meaning):
        name = "Broken"
        def description(self): return "Broken"
        def clarify(self): return None
        def reply(self): return None
        def path(self): return "Extract"
        def summarize(self): return None
        async def run(self, persona_response):
            raise RuntimeError("run exploded")

    memory = _memory([BrokenMeaning(p)])
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "task")
    memory.understand(memory.perceptions[0], BrokenMeaning(p))

    ollama.assert_call(
        run=lambda: conscious.decide(memory, p, _identity),
        response=_stream_json({"tool": "x", "recap": "trying"}),
    )

    executed = [s for s in memory.intentions[0].perception.thread if s.event == SignalEvent.executed]
    assert len(executed) == 1
    assert "run exploded" in executed[0].content
    _teardown()


def test_decide_recaps_when_action_returns_none():
    _setup()
    p = _persona()

    class NullActionMeaning(Meaning):
        name = "NullAction"
        def description(self): return "Null action"
        def clarify(self): return None
        def reply(self): return None
        def path(self): return "Extract"
        def summarize(self): return "Done"
        async def run(self, persona_response):
            return None

    memory = _memory([NullActionMeaning(p)])
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "task")
    memory.understand(memory.perceptions[0], NullActionMeaning(p))

    ollama.assert_call(
        run=lambda: conscious.decide(memory, p, _identity),
        response=_stream_json({"tool": "x", "recap": "nothing to do"}),
    )

    last = memory.intentions[0].perception.thread[-1]
    assert last.event == SignalEvent.recap
    assert last.content == "nothing to do"
    _teardown()


# ── Conclude ─────────────────────────────────────────────────────────────────

def test_conclude_does_nothing_when_no_thoughts():
    _setup()
    memory = _memory()
    import asyncio
    asyncio.run(conscious.conclude(memory, _persona(), _identity, _noop_say))
    _teardown()


def test_conclude_summarizes_with_model():
    _setup()
    p = _persona()
    memory = _memory()
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "task")
    thought = memory.understand(memory.perceptions[0], TestMeaning(p))
    memory.answer(thought, "done", SignalEvent.recap)

    said = []

    async def capture_say(text):
        said.append(text)

    ollama.assert_call(
        run=lambda: conscious.conclude(memory, p, _identity, capture_say),
        response={"message": {"content": "Task completed successfully."}},
    )

    assert said == ["Task completed successfully."]
    last = thought.perception.thread[-1]
    assert last.event == SignalEvent.summarized
    _teardown()


def test_conclude_uses_recap_when_no_summarize():
    _setup()
    p = _persona()
    memory = _memory()
    s = _signal()
    memory.trigger(s)
    memory.realize(s, "task")
    thought = memory.understand(memory.perceptions[0], NoSummaryMeaning(p))
    memory.answer(thought, "all done here", SignalEvent.recap)

    import asyncio
    asyncio.run(conscious.conclude(memory, p, _identity, _noop_say))

    last = thought.perception.thread[-1]
    assert last.event == SignalEvent.summarized
    assert last.content == "all done here"
    _teardown()
