from datetime import datetime

from application.core.brain.data import Signal, SignalEvent, Perception
from application.core.brain.perceptions import conversation, to_conversation, to_messages


def make_signal(event, content, ts=None):
    return Signal(
        id="s1",
        event=event,
        content=content,
        created_at=ts or datetime(2026, 3, 15, 10, 30),
    )


def test_it_formats_conversation_with_person_and_persona():
    p = Perception(impression="test", thread=[
        make_signal(SignalEvent.heard, "hello"),
        make_signal(SignalEvent.answered, "hi there"),
    ])
    result = conversation(p)
    assert "person: hello" in result
    assert "persona: hi there" in result


def test_it_excludes_internal_signals_from_conversation():
    p = Perception(impression="test", thread=[
        make_signal(SignalEvent.heard, "hello"),
        make_signal(SignalEvent.decided, "internal decision"),
        make_signal(SignalEvent.answered, "response"),
    ])
    result = conversation(p)
    assert "internal decision" not in result
    assert "person: hello" in result
    assert "persona: response" in result


def test_it_converts_signals_to_conversation_messages():
    signals = [
        make_signal(SignalEvent.heard, "hello"),
        make_signal(SignalEvent.answered, "hi"),
        make_signal(SignalEvent.heard, "how are you"),
    ]
    result = to_conversation(signals)
    assert len(result) == 3
    assert result[0] == {"role": "user", "content": "hello"}
    assert result[1] == {"role": "assistant", "content": "hi"}
    assert result[2] == {"role": "user", "content": "how are you"}


def test_it_coalesces_consecutive_same_role_messages():
    signals = [
        make_signal(SignalEvent.heard, "first"),
        make_signal(SignalEvent.queried, "second"),
        make_signal(SignalEvent.answered, "reply"),
    ]
    result = to_conversation(signals)
    assert len(result) == 2
    assert result[0]["content"] == "first\nsecond"
    assert result[0]["role"] == "user"


def test_it_includes_executed_signals_in_to_messages():
    signals = [
        make_signal(SignalEvent.heard, "run ls"),
        make_signal(SignalEvent.executed, "file1.txt\nfile2.txt"),
        make_signal(SignalEvent.answered, "here are your files"),
    ]
    result = to_messages(signals)
    assert any("file1.txt" in m["content"] for m in result)


def test_it_excludes_executed_signals_from_to_conversation():
    signals = [
        make_signal(SignalEvent.heard, "run ls"),
        make_signal(SignalEvent.executed, "file1.txt"),
        make_signal(SignalEvent.answered, "done"),
    ]
    result = to_conversation(signals)
    assert not any("file1.txt" in m["content"] for m in result)
