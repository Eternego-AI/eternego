"""Ego — the persona's reasoning and reply engine."""

from application.core.data import Persona, Prompt
from application.core.brain import character, current
from application.core import local_model, frontier, tools
from application.platform import logger


def identity(persona: Persona) -> str:
    """Build the character system prompt for this persona."""
    return character.shape(persona) + "\n\n" + current.situation(persona)


async def reason(persona: Persona, system: str, prompts: list[Prompt]) -> dict:
    """Call the persona's model in JSON mode. Returns a parsed JSON dict."""
    logger.info("ego.reason", {"persona": persona.id})
    full_system = identity(persona) + "\n\n" + system + "\n\nReturn your response as a JSON object."
    messages = [{"role": "system", "content": full_system}]
    messages += [{"role": p.role, "content": p.content} for p in prompts]
    return await local_model.chat_json_stream(persona.model.name, messages)


async def reply(persona: Persona, system: str, prompts: list[Prompt]):
    """Stream the persona's reply, yielding one paragraph at a time."""
    logger.info("ego.reply", {"persona": persona.id})
    full_system = identity(persona) + "\n\n" + system
    messages = [{"role": "system", "content": full_system}]
    messages += [{"role": p.role, "content": p.content} for p in prompts]
    async for paragraph in local_model.chat_stream_paragraph(persona.model.name, messages):
        yield paragraph


async def escalate(persona: Persona, thread_text: str,
                   existing_meanings: list) -> str | None:
    """Generate meaning code via frontier or local model. Returns Python source or None."""
    logger.info("ego.escalate", {"persona": persona.id})

    available_tools = tools.discover()
    existing = [{"name": m.name, "description": m.description()}
                for m in existing_meanings if m.name != "Escalation"]

    tools_text = "\n".join(
        f"- `{t.name}({', '.join(f'{k}: {v}' for k, v in t.params.items())}) -> {t.returns}`: {t.instruction}"
        for t in available_tools
    ) or "(no tools available)"

    meanings_text = "\n".join(
        f"- {m['name']}: {m['description']}" for m in existing
    ) or "(none yet)"

    prompt = (
        "# Meaning Generation\n\n"
        "You are defining a new Meaning class for a persona's cognitive system. "
        "A Meaning categorizes a type of interaction and tells the persona how to handle it.\n\n"
        f"## Conversation Thread\n\n{thread_text}\n\n"
        f"## Available Tools\n\n{tools_text}\n\n"
        f"## Existing Meanings (avoid duplicates)\n\n{meanings_text}\n\n"
        "## Task\n\n"
        "Generate a Python class that extends Meaning for this interaction.\n\n"
        "Rules:\n"
        "- Class must extend `Meaning` (imported from `application.core.brain.data`)\n"
        "- Set `name` as a class attribute (short, descriptive, e.g. 'System Check')\n"
        "- Implement: `description()`, `clarification()`, `reply()`, `path()`\n"
        "- `path()` returns None for conversational-only meanings\n"
        "- `path()` returns a prompt string for tool-using meanings — reference tools by "
        "their exact name (e.g. `linux.execute_on_sub_process`) and tell the model to "
        'return JSON like: {"tool": "name", "param": "value"}\n'
        "- Do NOT implement `run()` — the default handles tool dispatch\n"
        "- Do NOT add any imports beyond `from application.core.brain.data import Meaning`\n"
        "- Do NOT duplicate an existing meaning\n\n"
        "Return ONLY the Python source code. No markdown fences, no explanation.\n\n"
        "Example:\n\n"
        "from application.core.brain.data import Meaning\n\n\n"
        "class ExampleMeaning(Meaning):\n"
        '    name = "Example"\n\n'
        "    def description(self):\n"
        '        return "Description of what this meaning covers."\n\n'
        "    def clarification(self):\n"
        '        return "What to ask if unclear."\n\n'
        "    def reply(self):\n"
        '        return "How to respond to the person."\n\n'
        "    def path(self):\n"
        "        return None\n"
    )

    code = None
    if persona.frontier:
        try:
            response = await frontier.chat(persona.frontier, prompt)
            code = response.strip()
            if code.startswith("```"):
                lines = code.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                code = "\n".join(lines)
        except Exception as e:
            logger.warning("ego.escalate: frontier failed", {"error": str(e)})

    if not code:
        try:
            code = await local_model.generate(persona.model.name, prompt)
        except Exception as e:
            logger.warning("ego.escalate: local model failed", {"error": str(e)})

    return code or None
