"""Meanings — built-in and persona-specific meanings."""

import importlib.util

from application.core.brain.data import Meaning
from application.core.brain.mind.meanings.greeting import Greeting
from application.core.brain.mind.meanings.chatting import Chatting
from application.core.brain.mind.meanings.reminder import Reminder
from application.core.brain.mind.meanings.schedule import Scheduler
from application.core.brain.mind.meanings.calendar import Calendar
from application.core.brain.mind.meanings.noting import Noting
from application.core.brain.mind.meanings.recalling import Recalling
from application.core.brain.mind.meanings.shell import Shell
from application.core.brain.mind.meanings.todo import Todo
from application.core.brain.mind.meanings.escalation import Escalation
from application.core import paths
from application.platform import logger


def built_in(persona) -> list:
    """Return built-in meaning instances."""
    return [
        Greeting(persona),
        Chatting(persona),
        Reminder(persona),
        Scheduler(persona),
        Calendar(persona),
        Noting(persona),
        Recalling(persona),
        Shell(persona),
        Todo(persona),
        Escalation(persona),
    ]


def learn(persona, code: str) -> Meaning:
    """Save generated Python source as a persona-specific meaning, load and return it."""
    import re

    match = re.search(r"class\s+(\w+)\s*\(", code)
    if not match:
        raise ValueError("No class definition found in generated code")

    class_name = match.group(1)
    safe_name = re.sub(r"[^\w]", "_", class_name.lower()).strip("_")
    file_path = paths.meanings(persona.id) / f"{safe_name}.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(code)

    spec = importlib.util.spec_from_file_location(safe_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    cls = getattr(module, class_name)
    if not issubclass(cls, Meaning):
        raise ValueError(f"{class_name} does not extend Meaning")

    return cls(persona)


def specific_to(persona) -> list:
    """Load persona-specific meanings from Python files."""
    meanings_dir = paths.meanings(persona.id)
    if not meanings_dir.exists():
        return []

    result = []
    for file in sorted(meanings_dir.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr in dir(module):
                obj = getattr(module, attr)
                if (isinstance(obj, type) and issubclass(obj, Meaning)
                        and obj is not Meaning and hasattr(obj, "name")):
                    result.append(obj(persona))
        except Exception as e:
            logger.warning("meanings.specific_to: failed to load", {"file": str(file), "error": str(e)})

    return result
