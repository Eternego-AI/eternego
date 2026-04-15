"""Brain — recognize stage."""

from application.core import models
from application.core.brain import meanings
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
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
        system = (
            identity
            + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "# ▶ YOUR TASK: Recognize\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "You have these abilities — the activities you can actually perform:\n"
            + abilities + "\n"
            "0. None of the above — this task needs a capability I don't have yet\n\n"
            "Read the full conversation. Focus on the most recent unaddressed request or incomplete task. "
            "Ignore messages already handled.\n\n"
            "IMPORTANT: Match by CAPABILITY, not by topic.\n"
            "- If the task needs to run commands, check system state (disk, memory, files), browse the web, "
            "send emails, access external services, or do anything my listed abilities cannot literally DO → return 0.\n"
            "- Topic similarity is not enough. 'Check disk space' sounds adjacent to scheduling (both involve 'check') "
            "but scheduling can only SAVE reminders for the future, not check current state.\n"
            "- Do not force a match. Return 0 whenever no ability has the actual capability.\n\n"
            "Examples:\n"
            "- 'Remind me at 5pm' → 5 (scheduling CAN save reminders)\n"
            "- 'What's on my calendar?' → 4 (recalling CAN check scheduled events)\n"
            "- 'Check my disk space' → 0 (no ability can run commands)\n"
            "- 'Browse this website' → 0 (no ability can access the web)\n"
            "- 'How are you?' → 1 (chatting CAN have a conversation)\n\n"
            "Return JSON with the number:\n"
            '```json\n{"ability": 0}\n```'
        )
        prompt = [{"role": "system", "content": system}] + memory.prompts
        result = await models.chat_json(persona.thinking, prompt)
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
    system = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"# ▶ YOUR TASK: Generate a new meaning for {persona.name}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "## What is a Meaning\n\n"
        "A meaning is an activity the persona engages in — an ongoing cognitive process, "
        "not a static label or a command. It represents what the persona is DOING when it "
        "handles a particular kind of situation.\n\n"
        "A meaning has two parts:\n"
        "- **intention**: A sentence describing when this activity applies, written from "
        "the person's perspective (e.g. 'The person wants Primus to recall a past conversation').\n"
        "- **prompt**: The complete instruction set for the persona — what to do, which tools "
        "to use, what permissions to check, and what JSON format to return.\n\n"
        "Meanings are named as gerund nouns (e.g. 'scheduling', 'recalling', 'searching') "
        "because they describe activities — what the persona is engaged in, not what it is "
        "or what it has.\n\n"
        f"## Existing Meanings\n\n{existing}\n\n"
        f"## Available Tools\n\n{tools_doc}\n\n"
        "The new meaning's prompt can reference any of these tools.\n\n"
        "None of the existing meanings match the current conversation.\n"
        "Generate a new meaning that handles it.\n\n"
        "## What the Persona Knows\n\n"
        "The persona sees the following in every interaction:\n"
        "- **Person's identity**: factual data — name, job, family, contacts, relationships\n"
        "- **Person's traits**: behavioral patterns — preferences, habits, likes, dislikes\n"
        "- **Person's wishes**: long-term goals and aspirations\n"
        "- **Person's struggles**: ongoing difficulties and frustrations\n"
        "- **Persona's behavioral instructions**: how to communicate with this person\n"
        "- **Permissions**: what the persona is explicitly allowed or forbidden to do\n"
        "- **Notes**: explicitly saved reference data\n"
        "- **Today's schedule**: reminders and events due today\n"
        "- **Recent context**: what was recently discussed, decided, and committed to\n"
        "- **Current time and environment**: date, time, OS, workspace path\n\n"
        "The generated prompt can reference any of this — e.g. 'check the person's identity "
        "for their timezone', 'look at today's schedule for conflicts', 'review their wishes "
        "for relevant goals'.\n\n"
        f"## Workspace\n\n"
        f"The persona's workspace is: `{workspace}`\n"
        "Any created files, projects, or artifacts must be saved there.\n\n"
        "## Permission Guidelines\n\n"
        "The generated prompt MUST include a Permissions section that:\n"
        "- Identifies which tools in this meaning could be destructive or modify data\n"
        "- Instructs the persona to check its permissions before using those tools\n"
        "- If permission is lacking, the persona should explain what it would do and ask for permission\n"
        "- If permission has been explicitly rejected, instruct the person on how to do it themselves\n"
        "- Read-only tools and say do not require permissions\n\n"
        "## Meaning Structure\n\n"
        "A meaning is a Python module with two functions. Here is the stub with available properties:\n\n"
        "```python\n"
        '"""Meaning — gerund name."""\n\n'
        "from application.core import paths\n"
        "from application.core.data import Persona\n\n\n"
        "def intention(persona: Persona) -> str:\n"
        '    # persona.name — the persona\'s name\n'
        '    # persona.id — unique identifier\n'
        '    # persona.birthday — when the persona was created\n'
        '    return f"The person wants {persona.name} to ..."\n\n\n'
        "def prompt(persona: Persona) -> str:\n"
        '    # Available data via paths.read(path) — returns "" if file not found:\n'
        "    # paths.person_identity(persona.id) — person's factual identity\n"
        "    # paths.person_traits(persona.id) — person's behavioral patterns\n"
        "    # paths.wishes(persona.id) — person's long-term wishes\n"
        "    # paths.struggles(persona.id) — person's struggles\n"
        "    # paths.persona_trait(persona.id) — persona's behavioral instructions\n"
        "    # paths.permissions(persona.id) — granted/rejected permissions\n"
        "    # paths.notes(persona.id) — saved notes\n"
        "    # paths.history_briefing(persona.id) — past conversation index\n"
        "    # str(paths.workspace(persona.id)) — workspace directory path\n"
        '    return "# Title\\n\\n..."\n'
        "```\n\n"
        "Return JSON with the name and the complete Python source code:\n"
        "```json\n"
        '{"name": "gerund-noun (e.g. searching, deploying, reviewing)", '
        '"code": "the complete Python module source code"}\n'
        "```"
    )
    escalation_prompt = [{"role": "system", "content": system}] + memory.prompts

    model = persona.frontier if persona.frontier else persona.thinking
    try:
        result = await models.chat_json(model, escalation_prompt)
    except Exception:
        if model != persona.thinking:
            try:
                result = await models.chat_json(persona.thinking, escalation_prompt)
            except Exception:
                return False
        else:
            return False

    if not isinstance(result, dict):
        return False

    name = result.get("name", "")
    code = result.get("code", "")
    if not name or not code:
        return False

    saved_name = meanings.save_meaning(persona.id, name, code)
    memory.meaning = saved_name
    logger.debug("brain.recognize escalation result", {"persona": persona, "meaning": saved_name})
    return True
