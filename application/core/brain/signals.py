"""Signals — formatting helpers for Signal nodes."""

from application.core.brain.data import Signal


def as_chat(signal: Signal) -> str:
    """Format signal content with its timestamp — for use as Prompt.content where role is set separately."""
    ts = signal.created_at.strftime("%Y-%m-%d %H:%M UTC")
    return f"[{ts}] {signal.content}"


def as_text(signal: Signal) -> str:
    """Format a signal as a readable line, with timestamp and role."""
    ts = signal.created_at.strftime("%Y-%m-%d %H:%M UTC")
    return f"[{ts}] {signal.role}: {signal.content}"


def labeled(signal: Signal) -> str:
    """Format a signal with its ID, timestamp, role, and content — for routing tasks."""
    ts = signal.created_at.strftime("%Y-%m-%d %H:%M UTC")
    return f'id="{signal.id}" [{ts}] {signal.role}: {signal.content}'
