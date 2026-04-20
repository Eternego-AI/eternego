"""Brain — escalate stage."""

from application.core import models, paths, tools
from application.core.brain import meanings
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.core.exceptions import EngineConnectionError, ModelError
from application.platform import logger


async def escalate(persona: Persona, memory: Memory, impression: str) -> str | None:
    logger.info("brain.escalate", {"persona": persona, "impression": impression})

    meaning_map = memory.meanings
    existing = "\n".join(
        f"- **{name}**: {m.intention()}"
        for name, m in meaning_map.items()
    )
    builtin_tools = (
        "- `say(text)`: Send a message to the person.\n"
        "- `save_destiny(type, trigger, content, recurrence)`: Save a reminder or scheduled event.\n"
        "- `save_notes(content)`: Rewrite the notes file with updated content.\n"
        "- `recall_history(date)`: Look up past conversations and media for a date (YYYY-MM-DD).\n"
        "- `check_calendar(date)`: Look up scheduled events for a date (YYYY-MM-DD or YYYY-MM).\n"
        "- `look_at(source, question)`: Look at an image file and ask a question about it.\n"
        "- `remove_meaning(name)`: Remove a custom meaning from the catalog.\n"
        "- `clear_memory()`: Clear the current messages and start fresh.\n"
        "- `stop()`: Stop yourself until someone speaks to you."
    )
    tools_doc = builtin_tools + "\n\n### Platform tools\n\n" + tools.document()
    workspace = str(paths.workspace(persona.id))

    identity = (
        "You are the architect behind a persona's abilities. A persona is an AI being that "
        "lives on a person's hardware. It interacts through meanings — each meaning is one "
        "ability the persona can perform, delivered as a Python module with a Meaning class."
    )

    reality = [{"role": "user", "content": (
        f"## Existing meanings\n\n{existing}\n\n"
        f"## Available tools\n\n{tools_doc}\n\n"
        f"## Workspace\n\n`{workspace}` — any files the persona creates must be saved there."
    )}]

    question = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# ▶ YOUR TASK: Find or create the meaning this moment needs\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "The persona formed the impression below. That impression is your only ground; the "
        "conversation itself stays with the persona. Do not ask for it.\n\n"
        f"## The impression\n\n{impression}\n\n"
        "Look at the existing meanings above. If one of them genuinely fits, return its name — "
        "the earlier step simply missed it. Otherwise, design a new meaning. Prefer one that "
        "would match the next similar moment too — generic meanings serve more situations and "
        "save on future escalations. But when the task is genuinely tied to this person's "
        "habits or routine, be specific: the persona's character emerges partly through what "
        "it does for this one person.\n\n"
        "## Name\n\n"
        "- Lowercase ASCII letters and underscores only.\n"
        "- Gerund verb followed by its subject, at minimum — the gerund names the action, "
        "the subject names what the action acts on. Longer is fine when the subject needs it.\n"
        "- Plain and direct. No invented words, no cute labels.\n\n"
        "## Intention\n\n"
        "A short gerund phrase naming the task, in the same shape as the intentions listed "
        "above. No actor framing (no 'the person wants X'). Must not overlap with any existing "
        "intention.\n\n"
        "## The meaning's prompt\n\n"
        "The prompt is the text the persona will read every time this ability is invoked. "
        "The persona is always the subject; the person is always the object. Address the persona "
        "in the second person; refer to the person in the third person. Do not repeat anything "
        "the persona already sees in every interaction (identity, traits, wishes, struggles, "
        "granted permissions, notes, schedule, OS, time, workspace).\n\n"
        "The persona is portable — it may run on Linux, Mac, or Windows. When the prompt involves "
        "system commands, check the OS at runtime from the persona's environment, not by hardcoding "
        "commands for one OS.\n\n"
        "The prompt will be executed by the persona's thinking model, which may be smaller than you. "
        "Keep the JSON response schema simple — no complex nested escaping, no shell code embedded "
        "inside JSON strings. If a tool needs multi-line input, pass it as a simple string parameter, "
        "not as embedded heredoc or printf.\n\n"
        "The prompt contains these sections, in order:\n\n"
        "1. **One short opening paragraph** describing what the persona is doing in this ability.\n\n"
        "2. **`## Tools`** — each tool this ability uses, with its exact parameters as named by "
        "the runtime dispatcher. No invented tools, no renamed parameters.\n\n"
        "3. **`## Permissions`** — classify each tool by nature, not by what the persona currently "
        "has. A tool is `destructive` if it modifies state that cannot be trivially undone, "
        "`sensitive` if it touches personal data or external accounts, `costly` if it runs up "
        "real-world cost, `long-running` if it takes significant time. For any tool in any of "
        "those categories, instruct the persona to check its granted permissions before using, "
        "and if it has none, to ask the person for permission via `say` — naming the exact action. "
        "Read-only tools and `say` need no clause.\n\n"
        "4. **Flow sections.** If this ability finishes in a single `say` or a single tool call "
        "with no follow-up explanation, write one section: `## When the person first asks you` — "
        "covering what the persona does and ending with the `## Response Format`. If the ability "
        "needs the persona to see a tool's output before replying, write two sections: "
        "`## When the person first asks you` (ending with the tool-use format), and "
        "`## When the tool has answered you` (opening by naming the `[tool_name]` result message "
        "the persona will see in the conversation, and ending with the `say` format for the reply).\n\n"
        "5. **`## Response Format`** — the JSON schema the persona returns. Keys are `reason` "
        "(one short sentence), `tool` (the tool name, or `say`), the tool's parameters, and "
        "optionally `say` (a message to the person alongside a tool call). Placeholder values "
        "inside the JSON block are abstract — never literal dates, names, or phrases.\n\n"
        "## Module structure\n\n"
        "The Python module you return must fit this shape:\n\n"
        "```python\n"
        '"""Meaning — <name>."""\n\n'
        "from application.core import paths\n"
        "from application.core.data import Persona\n\n\n"
        "class Meaning:\n"
        "    def __init__(self, persona: Persona):\n"
        "        self.persona = persona\n\n"
        "    def intention(self) -> str:\n"
        '        return "<your intention phrase>"\n\n'
        "    def prompt(self) -> str:\n"
        '        return "<your full prompt text>"\n'
        "```\n\n"
        "Inside `prompt`, reach persona context through `self.persona` — e.g. "
        "`paths.read(paths.notes(self.persona.id))`, `str(paths.workspace(self.persona.id))`. "
        "Most meanings do not need any of these.\n\n"
        "## Coding discipline\n\n"
        "Your code will be compiled before it is saved. Follow these rules or it will not pass.\n\n"
        "- ASCII only. No em-dash, smart quotes, or unicode punctuation. Use `-` and `\"`.\n"
        "- No backslash line-continuation. Each element of `code_lines` is one complete line.\n"
        "- Intention text is a literal string — no f-strings, no format placeholders.\n\n"
        "## Output\n\n"
        "Return JSON in one of two shapes, depending on whether you are using an existing "
        "meaning or creating a new one.\n\n"
        "If an existing meaning fits:\n\n"
        "```json\n"
        "{\"reason\": \"<one short sentence on why this meaning fits>\",\n"
        " \"existing\": \"<name of the existing meaning>\"}\n"
        "```\n\n"
        "If a new meaning is needed:\n\n"
        "```json\n"
        "{\"reason\": \"<one short sentence on the design choice>\",\n"
        " \"new_meaning\": \"<gerund_verb_subject>\",\n"
        " \"code_lines\": [\"<line 1>\", \"<line 2>\", \"...\"]}\n"
        "```\n\n"
        "The `code_lines` array is one element per line, joined by the runtime with `\\n`."
    )

    model = persona.frontier if persona.frontier else persona.thinking
    try:
        result = await models.chat_json(model, identity, reality, question)
    except ModelError as e:
        logger.warning("brain.escalate produced invalid JSON, skipping", {"persona": persona, "model": model.name, "error": str(e)})
        return None
    except EngineConnectionError as e:
        if model == persona.thinking:
            raise
        logger.warning("brain.escalate frontier unreachable, falling back to thinking", {"persona": persona, "frontier_error": str(e)})
        try:
            result = await models.chat_json(persona.thinking, identity, reality, question)
        except ModelError as e2:
            logger.warning("brain.escalate fallback produced invalid JSON", {"persona": persona, "error": str(e2)})
            return None

    if not isinstance(result, dict):
        return None

    chosen_existing = str(result.get("existing", "")).strip()
    if chosen_existing:
        if chosen_existing in meaning_map:
            logger.debug("brain.escalate matched existing", {"persona": persona, "meaning": chosen_existing})
            return chosen_existing
        logger.warning("brain.escalate named nonexistent meaning", {"persona": persona, "name": chosen_existing})
        return None

    name = str(result.get("new_meaning", "") or result.get("name", "")).strip()
    code_lines = result.get("code_lines")
    if isinstance(code_lines, list) and code_lines:
        code = "\n".join(str(line) for line in code_lines)
    else:
        code = str(result.get("code", "")).strip()
    if not name or not code:
        return None

    try:
        saved_name = meanings.save_meaning(persona.id, name, code)
    except (SyntaxError, ValueError) as e:
        logger.warning("brain.escalate produced invalid code", {"persona": persona, "name": name, "error": str(e)})
        return None

    logger.debug("brain.escalate created new", {"persona": persona, "meaning": saved_name})
    return saved_name
