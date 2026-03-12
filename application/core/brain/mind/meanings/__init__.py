"""Meanings — all built-in meanings available to the mind."""

from application.core.brain.mind.meanings.greeting import Greeting
from application.core.brain.mind.meanings.chatting import Chatting
from application.core.brain.mind.meanings.setting_reminder import SettingReminder
from application.core.brain.mind.meanings.scheduling_event import SchedulingEvent
from application.core.brain.mind.meanings.escalation import Escalation


def all_meanings(persona) -> list:
    """Return all known Meaning instances for this persona."""
    return [
        Greeting(persona),
        Chatting(persona),
        SettingReminder(persona),
        SchedulingEvent(persona),
        Escalation(persona),
    ]
