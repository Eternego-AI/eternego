"""Meanings — all built-in meanings available to the brain."""

from application.core.brain.meanings.greeting import Greeting
from application.core.brain.meanings.chatting import Chatting
from application.core.brain.meanings.setting_reminder import SettingReminder
from application.core.brain.meanings.scheduling_event import SchedulingEvent
from application.core.brain.meanings.escalation import Escalation


def all_meanings(persona) -> list:
    """Return all known Meaning instances for this persona."""
    return [
        Greeting(persona),
        Chatting(persona),
        SettingReminder(persona),
        SchedulingEvent(persona),
        Escalation(persona),
    ]
