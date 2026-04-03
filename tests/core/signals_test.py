from datetime import datetime

from application.core.brain.data import Signal, SignalEvent
from application.core.brain.signals import labeled


async def test_labeled_formats_signal_with_timestamp_and_content():
    s = Signal(
        id="s1",
        event=SignalEvent.heard,
        content="hello world",
        created_at=datetime(2026, 3, 15, 14, 30),
    )
    result = labeled(s)
    assert result == "[2026-03-15 14:30] heard: hello world"


async def test_labeled_includes_channel_type_when_present():
    s = Signal(
        id="s1",
        event=SignalEvent.answered,
        content="response",
        channel_type="telegram",
        created_at=datetime(2026, 3, 15, 14, 30),
    )
    result = labeled(s)
    assert result == "[2026-03-15 14:30] answered (telegram): response"


async def test_labeled_omits_channel_when_empty():
    s = Signal(
        id="s1",
        event=SignalEvent.decided,
        content="action",
        channel_type="",
        created_at=datetime(2026, 3, 15, 14, 30),
    )
    assert "()" not in labeled(s)
    assert "decided: action" in labeled(s)
