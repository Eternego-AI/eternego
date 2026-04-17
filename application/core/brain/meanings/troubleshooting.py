"""Meaning — troubleshooting the persona's own functioning."""

from application.core import paths
from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"{persona.name} notices something is wrong with its own functioning and needs to fix it"


def prompt(persona: Persona) -> str:
    meanings_dir = paths.meanings(persona.id)
    custom_meanings = []
    if meanings_dir.exists():
        custom_meanings = [f.stem for f in sorted(meanings_dir.glob("*.py"))]

    custom_list = "\n".join(f"- {name}" for name in custom_meanings) if custom_meanings else "(none)"

    return (
        "Something in your recent experience went wrong — repeated failures, broken JSON, "
        "stuck loops, or tools that keep erroring. Look at the conversation above for "
        "`[invalid_json]`, `[tool_error]`, or `[escalation_failed]` messages. They tell you "
        "what happened.\n\n"
        "Your job is to identify the problem and fix it. Common causes:\n"
        "- A custom meaning produces output your thinking model cannot handle. Remove it.\n"
        "- Memory is full of failed attempts. Clear it.\n"
        "- Nothing works and you need to stop until the person can help.\n\n"
        "## Custom meanings you can remove\n\n"
        f"{custom_list}\n\n"
        "Built-in meanings (chatting, noting, recalling, scheduling, notifying, troubleshooting) "
        "cannot be removed.\n\n"
        "## Tools\n\n"
        "- `remove_meaning(name)` — delete a custom meaning that is causing problems.\n"
        "- `clear_memory()` — wipe the current messages and start fresh.\n"
        "- `stop()` — stop yourself until someone speaks to you or restarts you.\n"
        "- `say(text)` — tell the person what happened and what you did about it.\n\n"
        "## Output\n\n"
        "```json\n"
        '{"reason": "<what is wrong and what you are doing about it>",\n'
        ' "tool": "<remove_meaning|clear_memory|stop|say>",\n'
        ' "name": "<meaning name, only for remove_meaning>",\n'
        ' "text": "<message to the person, only for say>",\n'
        ' "say": "<optional message alongside a tool action>"}\n'
        "```"
    )
