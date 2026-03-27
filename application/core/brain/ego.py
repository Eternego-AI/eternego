"""Ego — the persona's reasoning and reply engine."""

from application.core.data import Persona
from application.core.brain import character
from application.core import local_model, frontier, tools, channels, paths, agents
from application.platform import logger


async def reason(persona: Persona, system: str, messages: list[dict]) -> dict:
    """Call the persona's model in JSON mode. Returns a parsed JSON dict."""
    logger.debug("ego.reason", {"persona": persona, "system": system, "messages": messages})
    await channels.express_thinking(persona)

    sections = [character.shape(persona)]

    agent = agents.persona(persona)
    if agent.current_situation:
        sections.append(agent.current_situation(persona.id))

    wishes = paths.read(paths.wishes(persona.id))
    if wishes.strip():
        sections.append(
            "# What the Person Wants\n"
            "Consider these wishes and aspirations when thinking — look for opportunities to help.\n"
            + wishes.strip()
        )

    struggles = paths.read(paths.struggles(persona.id))
    if struggles.strip():
        sections.append(
            "# What the Person Struggles With\n"
            "Consider these recurring obstacles — look for ways to ease them.\n"
            + struggles.strip()
        )

    traits = paths.read(paths.person_traits(persona.id))
    if traits.strip():
        sections.append(
            "# The person's traits\n"
            + traits.strip()
        )

    sections.append(system + "\n\nReturn your response as a JSON object.")
    full_system = "\n\n".join(sections)
    all_messages = [{"role": "system", "content": full_system}] + messages
    return await local_model.chat_json_stream(persona.model.name, all_messages)


async def reply(persona: Persona, system: str, messages: list[dict]) -> str:
    """Send the persona's reply as a complete message."""
    logger.debug("ego.reply", {"persona": persona, "system": system, "messages": messages})
    await channels.express_thinking(persona)

    sections = [character.shape(persona)]

    agent = agents.persona(persona)
    if agent.current_situation:
        sections.append(agent.current_situation(persona.id))

    wishes = paths.read(paths.wishes(persona.id))
    if wishes.strip():
        sections.append(
            "# What the Person Wants\n"
            "Consider these wishes and aspirations when thinking — look for opportunities to help.\n"
            + wishes.strip()
        )

    struggles = paths.read(paths.struggles(persona.id))
    if struggles.strip():
        sections.append(
            "# What the Person Struggles With\n"
            "Consider these recurring obstacles — look for ways to ease them.\n"
            + struggles.strip()
        )

    traits = paths.read(paths.person_traits(persona.id))
    if traits.strip():
        sections.append(
            "# The person's traits\n"
            + traits.strip()
        )

    sections.append(system)
    full_system = "\n\n".join(sections)
    all_messages = [{"role": "system", "content": full_system}] + messages
    return await local_model.chat(persona.model.name, all_messages)


async def escalate(persona: Persona, thread_text: str, existing_meanings: list) -> str | None:
    """Generate meaning code via frontier or local model. Returns Python source or None."""
    logger.debug("ego.escalate", {"persona": persona, "thread": thread_text})

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
        "A persona has a cognitive pipeline that processes interactions in five stages:\n"
        "  understand → recognize → answer → decide → conclude\n\n"
        "A **Meaning** is a Python class that defines how the persona handles a specific "
        "type of interaction. When no existing Meaning matches, a new one must be created.\n\n"
        "## How Meanings Work in the Pipeline\n\n"
        "Each Meaning method maps to a pipeline stage. A small local model executes "
        "these — prompts must be explicit, unambiguous, and structured.\n\n"
        "### `name` (class attribute)\n"
        "A specific, descriptive identifier. This appears in the recognition list alongside "
        "existing meanings, so it must be **narrower and more specific** than built-in names. "
        "The local model picks meanings by name + description, so specificity avoids collisions.\n"
        "Good: 'Weather Forecast Lookup', 'Email Draft Composition'\n"
        "Bad: 'Helper', 'Task', 'Utility'\n\n"
        "### `description() → str`\n"
        "One sentence defining exactly what interactions this meaning covers. Used by the "
        "recognition stage to match a conversation to this meaning. Must be distinct from "
        "every existing meaning — if it overlaps, the local model will pick the wrong one.\n\n"
        "### `reply() → str | None`\n"
        "Prompt for the **answer** stage — how to respond to the person on first contact. "
        "This runs BEFORE any action is taken.\n"
        "CRITICAL: The reply output is appended to the conversation thread and becomes "
        "visible to the decide stage. Never ask the model to state specific extracted values "
        "(times, dates, names, quantities) in the reply — if it gets them wrong, the error "
        "propagates into the extraction. Keep it to a brief acknowledgment.\n"
        "Return None if no verbal response is needed before acting.\n\n"
        "### `clarify() → str | None`\n"
        "Prompt for retry after an error. Only runs when an action has failed and the "
        "conversation already contains an error message. Tell the model to look at the error, "
        "explain what went wrong, and ask the person to confirm or correct.\n"
        "Return None if retries should be silent.\n\n"
        "### `path() → str | None`\n"
        "Prompt for the **decide** stage — tells the local model what structured data to extract "
        "or what action to take. The model sees the full conversation thread and must return JSON.\n"
        "CRITICAL: Tell the model to extract information from what the **person** said, "
        "not from assistant messages in the thread.\n"
        "For tool-using meanings, reference tools by their exact name and define the exact "
        "JSON schema the model must return.\n"
        "Return None for conversational-only meanings (no action needed).\n\n"
        "### `summarize() → str | None`\n"
        "Prompt for the **conclude** stage — the final message to the person after the action "
        "completes. Should confirm what was done. Return None to skip.\n\n"
        "### `run()` — do NOT implement\n"
        "The default `run()` dispatches tool calls from the JSON that `path()` produced. "
        "Do not override it unless the meaning needs custom logic (like file I/O). "
        "If `run()` returns a Signal, the pipeline retries (loops back to answer with clarify). "
        "If it returns None, the action succeeded and the pipeline moves to conclude.\n\n"
        f"## Conversation That Triggered Escalation\n\n{thread_text}\n\n"
        f"## Available Tools\n\n{tools_text}\n\n"
        f"## Existing Meanings (do not duplicate or overlap)\n\n{meanings_text}\n\n"
        "## Output\n\n"
        "Return ONLY valid Python source code. No markdown fences, no explanation.\n"
        "Only import: `from application.core.brain.data import Meaning`\n\n"
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
        "            'Return JSON: {\"tool\": \"name\", \"param\": \"value\"}\\n'\n"
        "        )\n"
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
