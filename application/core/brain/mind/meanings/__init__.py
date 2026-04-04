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
from application.core.brain.mind.meanings.coding import Coding
from application.core.brain.mind.meanings.due_notification import DueNotification
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
        Coding(persona),
        DueNotification(persona),
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


def document() -> str:
    """Return a description of what a Meaning is, how each method works, and a real example.

    WARNING: This document is used in escalation prompts to teach models how to
    generate new meanings. If you change the Meaning abstract class, add/remove
    methods, or change how run() dispatches tools, update this document to match.
    The example meaning (Reminder) should be kept representative of a good meaning.
    """
    return (
        "A Meaning is a Python class that defines how one type of interaction flows\n"
        "through the pipeline. Each method is a prompt that a local model executes.\n\n"
        "### Methods\n\n"
        "**name** (class attribute) — A specific, descriptive identifier. Must be\n"
        "  narrower and more specific than existing meanings to avoid collisions.\n"
        "  Good: 'Weather Forecast Lookup'. Bad: 'Helper', 'Task'.\n\n"
        "**description() → str** — One sentence defining what interactions this covers.\n"
        "  Used by the understand step to match conversations to this meaning.\n\n"
        "**reply() → str | None** — Prompt for the recognize step. Generates the first\n"
        "  response to the person BEFORE any action. Return None to skip.\n"
        "  CRITICAL: Keep replies vague — never state extracted values. Errors propagate.\n\n"
        "**clarify() → str | None** — Prompt for retry after an error. Tell the model to\n"
        "  look at the error and ask the person to correct. Return None for silent retry.\n\n"
        "**path() → str | None** — Prompt for the decide step. Tells the model what\n"
        "  structured data to extract. Must return JSON.\n"
        "  For tools: {\"tool\": \"tool_name\", ...params}.\n"
        "  CRITICAL: Extract from what the person said, not from assistant messages.\n"
        "  Return None for conversational-only meanings.\n\n"
        "**summarize() → str | None** — Prompt for the conclude step. Confirms what was\n"
        "  done. Return None to skip.\n\n"
        "**run(persona_response: dict)** — Do NOT override unless custom logic is needed.\n"
        "  The default dispatches tool calls from the JSON that path() produced.\n\n"
        "### Example: Reminder\n\n"
        "```python\n"
        "from application.core.brain.data import Meaning\n"
        "from application.core import paths\n\n"
        "class Reminder(Meaning):\n"
        '    name = "Reminder"\n\n'
        "    def description(self):\n"
        '        return "The person asks to CREATE or SET a new reminder for a future time."\n\n'
        "    def clarify(self):\n"
        "        return (\n"
        '            "The previous attempt to set the reminder failed. "\n'
        '            "Look at the error, explain what went wrong, and ask the person to correct."\n'
        "        )\n\n"
        "    def reply(self):\n"
        '        return "Acknowledge briefly that you will set the reminder. Do not state the time or details."\n\n'
        "    def summarize(self):\n"
        '        return "The reminder has been set. Confirm the time and what it is about."\n\n'
        "    def path(self):\n"
        "        return (\n"
        '            "Extract the reminder details from what the person said.\\n"\n'
        "            'Return JSON: {\"trigger\": \"YYYY-MM-DD HH:MM\", \"content\": \"what to remind\"}\\n'\n"
        "        )\n\n"
        "    async def run(self, persona_response):\n"
        "        trigger = persona_response.get('trigger', '')\n"
        "        content = persona_response.get('content', '')\n"
        "        if not trigger or not content:\n"
        "            raise ValueError('trigger or content is missing')\n"
        "        async def action():\n"
        "            paths.save_destiny_entry(self.persona.id, 'reminder', trigger, content)\n"
        "        return action\n"
        "```"
    )


def prompt(existing_meanings: list) -> str:
    """Format existing meanings as a prompt section for the model."""
    entries = [
        f"- {m.name}: {m.description()}"
        for m in existing_meanings if m.name != "Escalation"
    ]
    return "\n".join(entries) if entries else "(none yet)"


def stub() -> str:
    """Return the Python stub template for a new Meaning class.

    WARNING: This stub must match the Meaning abstract class signature.
    If you add or remove methods from Meaning, update this stub to match.
    """
    return (
        "from application.core.brain.data import Meaning\n\n\n"
        "class SpecificDescriptiveName(Meaning):\n"
        '    name = "Specific Descriptive Name"\n\n'
        "    def description(self):\n"
        '        return "Narrow, specific description of what this covers."\n\n'
        "    def clarify(self):\n"
        '        return "Look at the error. Explain what went wrong and ask the person to correct."\n\n'
        "    def reply(self):\n"
        '        return "Acknowledge briefly. Do not restate extracted details."\n\n'
        "    def summarize(self):\n"
        '        return "Confirm what was done."\n\n'
        "    def path(self):\n"
        "        return (\n"
        '            "Extract X from what the person said (ignore assistant messages).\\n"\n'
        "            'Return JSON: {\"tool\": \"tool_name\", ...params}\\n'\n"
        "        )\n"
    )


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
