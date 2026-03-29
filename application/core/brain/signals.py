"""Signals — formatting helpers for Signal nodes."""

from application.core.brain.data import Signal


def labeled(signal: Signal) -> str:
    """Format a signal with timestamp, event, and content — for routing tasks."""
    ts = signal.created_at.strftime("%Y-%m-%d %H:%M")
    channel = f" ({signal.channel_type})" if signal.channel_type else ""
    return f"[{ts}] {signal.event}{channel}: {signal.content}"
