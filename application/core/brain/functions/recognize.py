"""Brain — recognize stage."""

from application.core import models
from application.core.brain import meanings
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Persona, Prompt
from application.platform import logger


async def recognize(persona: Persona, identity: str, memory: Memory) -> bool:
    meaning_map = meanings.available(persona)
    meaning_names = list(meaning_map.keys())
    logger.debug("brain.recognize", {"persona": persona, "messages": memory.messages, "meanings_available": meaning_names})

    try:
        abilities = "\n".join(
            f"{i}. {meaning_map[name].intention(persona)}"
            for i, name in enumerate(meaning_names, 1)
        )
        n = len(meaning_names)
        question = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "# ▶ YOUR TASK: Recognize what this moment calls for\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Pick the ability — from the list below — that fits what the conversation now needs. "
            f"The need may be a reply to what was just said, a continuation of a thread you were on, "
            f"or an action you're choosing to take. Match by capability, not by topic. Return 0 when "
            f"no listed ability can actually do what is needed (e.g. anything requiring shell, live "
            f"system state, the web, or external services not listed).\n\n"
            "## Abilities\n\n"
            + abilities + "\n\n"
            "## Output\n\n"
            "```json\n"
            '{"reason": "<one short sentence>",\n'
            f' "ability": <integer 0 to {n}>}}\n'
            "```"
        )
        result = await models.chat_json(persona.thinking, identity, memory.prompts, question)
        if isinstance(result, dict):
            raw = result.get("ability", 0)
            try:
                idx = int(raw)
            except (TypeError, ValueError):
                if isinstance(raw, str):
                    match = raw.strip().lower()
                    for name in meaning_names:
                        if name == match or name.startswith(match):
                            memory.meaning = name
                            logger.debug("brain.recognize selected", {"persona": persona, "meaning": memory.meaning})
                            return True
                idx = 0
            if 1 <= idx <= len(meaning_names):
                memory.meaning = meaning_names[idx - 1]
                logger.debug("brain.recognize selected", {"persona": persona, "meaning": memory.meaning})
                return True
    except Exception as e:
        logger.warning("brain.recognize matching failed", {"persona": persona, "error": str(e), "meanings_available": meaning_names})

    logger.debug("brain.recognize escalating", {"persona": persona, "meanings_available": meaning_names})

    existing = "\n".join(
        f"- **{name}**: {m.intention(persona)}"
        for name, m in meaning_map.items()
    )
    from application.core import paths, tools
    builtin_tools = (
        "- `say(text)`: Send a message to the person.\n"
        "- `save_destiny(type, trigger, content, recurrence)`: Save a reminder or scheduled event.\n"
        "- `save_notes(content)`: Rewrite the notes file with updated content.\n"
        "- `recall_history(date)`: Look up past conversations for a date (YYYY-MM-DD).\n"
        "- `check_calendar(date)`: Look up scheduled events for a date (YYYY-MM-DD or YYYY-MM)."
    )
    tools_doc = builtin_tools + "\n\n### Platform tools\n\n" + tools.document()
    workspace = str(paths.workspace(persona.id))

    escalation_system = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"# ▶ YOUR TASK: Find or create the meaning this moment needs\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "A meaning is an ability the persona can perform. An earlier step did not match any "
        "existing meaning to what this moment calls for, and escalated to you.\n\n"
        "Look at the existing meanings below and the conversation above. If one of them "
        "genuinely fits, return its name — the earlier step simply missed it. Otherwise, create "
        "a new meaning: pick a name, write an intention, and write the prompt the persona will "
        "read every time this ability is invoked — all delivered as a Python module.\n\n"
        f"## Existing meanings\n\n{existing}\n\n"
        "## Name\n\n"
        "The name is how this ability is identified in the persona's catalog of what it can do.\n\n"
        "- Always in English, regardless of the language the person uses.\n"
        "- Lowercase ASCII letters and underscores only.\n"
        "- Gerund verb followed by its subject, at minimum — the gerund names the action, the "
        "subject names what the action acts on. `checking_disk_space`, not `checking`. "
        "`drafting_email_reply`, not `drafting`. Longer is fine when the subject needs it.\n"
        "- Plain and direct. No invented words, no cute labels, no abstractions.\n\n"
        "## Intention\n\n"
        "The intention is one sentence that names the situation in which this ability applies. "
        f"It must read: `The person wants {persona.name} to <specific verb phrase>`.\n\n"
        "To write the verb phrase: imagine what you would ask a trusted friend to do for you, "
        "and phrase it concretely. The sentence must be specific enough that a reader can tell "
        "at a glance what kind of request it matches, and general enough that many variations "
        "of the same kind of request all fit. It must not overlap with any existing meaning's "
        "intention above.\n\n"
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
        "optionally `say` (a message to the person alongside a tool call). All example values "
        "inside the JSON block are abstract placeholders like `<YYYY-MM-DD>` or `<your reply>` — "
        "never literal dates, names, or phrases the person might have used.\n\n"
        "## Available tools\n\n"
        f"{tools_doc}\n\n"
        f"## Workspace\n\n`{workspace}` — any files the persona creates must be saved there.\n\n"
        "## Module structure\n\n"
        "The Python module you return must fit this shape, with your chosen name, intention, "
        "and prompt substituted as literals:\n\n"
        "```python\n"
        '"""Meaning — <name>."""\n\n'
        "from application.core import paths\n"
        "from application.core.data import Persona\n\n\n"
        "def intention(persona: Persona) -> str:\n"
        '    return "<your full intention sentence>"\n\n\n'
        "def prompt(persona: Persona) -> str:\n"
        '    return "<your full prompt text>"\n'
        "```\n\n"
        "Inside `prompt`, you may read persona files if the prompt genuinely needs them:\n"
        "`paths.read(paths.notes(persona.id))`, `paths.read(paths.history_briefing(persona.id))`, "
        "or `str(paths.workspace(persona.id))`. Most meanings do not need any of these.\n\n"
        "## Coding discipline\n\n"
        "Your code will be compiled before it is saved. Follow these rules or it will not pass.\n\n"
        "- ASCII only. No em-dash `—`, smart quotes, or unicode punctuation. Use `-` and `\"`.\n"
        "- No backslash line-continuation. Each element of `code_lines` is one complete line.\n"
        "- Substitute literals, not placeholders. Write the persona's actual name in the "
        f"intention — not `<persona.name>`. For this persona, write `{persona.name}`.\n\n"
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
        " \"code_lines\": [\"\\\"\\\"\\\"Meaning — <name>.\\\"\\\"\\\"\", \"\", \"from application.core import paths\", \"...\"]}\n"
        "```\n\n"
        "The `code_lines` array is one element per line, joined by the runtime with `\\n`."
    )
    model = persona.frontier if persona.frontier else persona.thinking
    try:
        result = await models.chat_json(model, "", memory.prompts, escalation_system)
    except Exception:
        if model != persona.thinking:
            try:
                result = await models.chat_json(persona.thinking, "", memory.prompts, escalation_system)
            except Exception:
                struggle = "[escalation_failed] You tried to understand what this asks of you, and with the abilities you have, you could not. You do not understand this meaning yet."
                memory.add(Message(
                    content=struggle,
                    prompt=Prompt(role="user", content=struggle),
                ))
                return False
        else:
            struggle = "[escalation_failed] You tried to understand what this asks of you, and with the abilities you have, you could not. You do not understand this meaning yet."
            memory.add(Message(
                content=struggle,
                prompt=Prompt(role="user", content=struggle),
            ))
            return False

    if not isinstance(result, dict):
        struggle = "[escalation_failed] You tried to understand what this asks of you, and with the abilities you have, you could not. You do not understand this meaning yet."
        memory.add(Message(
            content=struggle,
            prompt=Prompt(role="user", content=struggle),
        ))
        return False

    chosen_existing = str(result.get("existing", "")).strip()
    if chosen_existing:
        if chosen_existing in meaning_map:
            memory.meaning = chosen_existing
            logger.debug("brain.recognize escalation matched existing", {"persona": persona, "meaning": chosen_existing})
            return True
        logger.warning("brain.recognize escalation named nonexistent meaning", {"persona": persona, "name": chosen_existing})
        struggle = "[escalation_failed] You tried to understand what this asks of you, and with the abilities you have, you could not. You do not understand this meaning yet."
        memory.add(Message(
            content=struggle,
            prompt=Prompt(role="user", content=struggle),
        ))
        return False

    name = str(result.get("new_meaning", "") or result.get("name", "")).strip()
    code_lines = result.get("code_lines")
    if isinstance(code_lines, list) and code_lines:
        code = "\n".join(str(line) for line in code_lines)
    else:
        code = str(result.get("code", "")).strip()
    if not name or not code:
        struggle = "[escalation_failed] You tried to understand what this asks of you, and with the abilities you have, you could not. You do not understand this meaning yet."
        memory.add(Message(
            content=struggle,
            prompt=Prompt(role="user", content=struggle),
        ))
        return False

    try:
        saved_name = meanings.save_meaning(persona.id, name, code)
    except (SyntaxError, ValueError) as e:
        logger.warning("brain.recognize escalation produced invalid code", {"persona": persona, "name": name, "error": str(e)})
        struggle = "[escalation_failed] You tried to understand what this asks of you, and with the abilities you have, you could not. You do not understand this meaning yet."
        memory.add(Message(
            content=struggle,
            prompt=Prompt(role="user", content=struggle),
        ))
        return False

    memory.meaning = saved_name
    logger.debug("brain.recognize escalation created new", {"persona": persona, "meaning": saved_name})
    return True
