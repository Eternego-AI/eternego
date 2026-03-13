"""Subconscious — sleep-time knowledge extraction.

Each function receives (persona, conversations), builds a single prompt,
uses ego.reply to stream the result, and saves directly to the relevant file.
"""

from application.core.data import Prompt
from application.core.brain import ego
from application.core import paths
from application.platform import logger


async def person_identity(persona, conversations: str) -> None:
    """Extract and merge identity facts."""
    existing = paths.read(paths.person_identity(persona.id))
    system = (
        "# Identity Fact Maintenance\n\n"
        "You maintain a list of concrete, enduring facts about a person: "
        "names, dates, places, relationships, possessions, job details, timezone.\n\n"
        f"## Conversations\n\n{conversations}\n\n"
        f"## Known Facts\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "Extract new facts from the conversations and merge with the known facts. "
        "Combine duplicates into single statements. Note contradictions. "
        "Drop anything already captured.\n\n"
        "Pay attention to timezone changes — if the person mentions travel, "
        "relocation, or being in a different city, update their timezone accordingly "
        "(e.g. 'The person's timezone is Asia/Tokyo from March 15 to March 22').\n\n"
        "EXCLUDE: reminders, scheduled events, to-do items, tool commands and outputs, "
        "system operations — these are transient, not identity.\n\n"
        "Return the complete merged list — one fact per line, no bullets, no headers."
    )
    prompts = [Prompt(role="user", content="Process the input above.")]
    parts = []
    async for paragraph in ego.reply(persona, system, prompts):
        parts.append(paragraph)
    result = "\n".join(parts)
    if result:
        logger.info("subconscious.person_identity", {"persona": persona.id})
        paths.save_as_string(paths.person_identity(persona.id), result)


async def person_traits(persona, conversations: str) -> None:
    """Extract and merge behavioral traits."""
    existing = paths.read(paths.person_traits(persona.id))
    system = (
        "# Behavioral Trait Maintenance\n\n"
        "You maintain a list of the person's behavioral preferences and recurring patterns: "
        "communication style, work habits, decision-making patterns, preferences.\n\n"
        f"## Conversations\n\n{conversations}\n\n"
        f"## Known Traits\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "Extract new traits from the conversations and merge with the known traits. "
        "A trait is a pattern of HOW the person behaves, not WHAT they asked you to do. "
        "Combine entries that describe the same pattern into a single stronger statement. "
        "Remove duplicates. Be specific — not 'likes coding' but 'prefers Python for scripting'.\n\n"
        "EXCLUDE: specific requests (reminders, schedules, commands), tool outputs, "
        "one-off actions — these are tasks, not traits.\n\n"
        "Return the complete merged list — one trait per line, no bullets, no headers."
    )
    prompts = [Prompt(role="user", content="Process the input above.")]
    parts = []
    async for paragraph in ego.reply(persona, system, prompts):
        parts.append(paragraph)
    result = "\n".join(parts)
    if result:
        logger.info("subconscious.person_traits", {"persona": persona.id})
        paths.save_as_string(paths.person_traits(persona.id), result)


async def wishes(persona, conversations: str) -> None:
    """Extract and merge wishes and aspirations."""
    existing = paths.read(paths.wishes(persona.id))
    system = (
        "# Wish Maintenance\n\n"
        "You maintain a list of the person's deeper desires, life goals, and aspirations — "
        "things they genuinely want in life, not tasks they asked you to perform.\n\n"
        f"## Conversations\n\n{conversations}\n\n"
        f"## Known Wishes\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "Extract genuine wants from the conversations — long-term desires and goals. "
        "Merge with known wishes. Combine entries that express the same underlying desire. "
        "Remove duplicates.\n\n"
        "EXCLUDE: reminders, scheduled events, specific requests ('remind me to...', "
        "'check my storage'), tool operations — these are tasks, not wishes. "
        "A wish is something like 'wants to travel more' or 'wants to learn Japanese', "
        "not 'wants to be reminded to call a friend'.\n\n"
        "Return the complete merged list — one wish per line, no bullets, no headers."
    )
    prompts = [Prompt(role="user", content="Process the input above.")]
    parts = []
    async for paragraph in ego.reply(persona, system, prompts):
        parts.append(paragraph)
    result = "\n".join(parts)
    if result:
        logger.info("subconscious.wishes", {"persona": persona.id})
        paths.save_as_string(paths.wishes(persona.id), result)


async def struggles(persona, conversations: str) -> None:
    """Extract and merge recurring struggles."""
    existing = paths.read(paths.struggles(persona.id))
    system = (
        "# Struggle Maintenance\n\n"
        "You maintain a list of the person's recurring obstacles and friction points: "
        "things they repeatedly find difficult, inefficient, or frustrating.\n\n"
        f"## Conversations\n\n{conversations}\n\n"
        f"## Known Struggles\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "Extract recurring friction from the conversations — patterns that suggest "
        "ongoing difficulty, not one-off issues. "
        "Merge with known struggles. Combine entries that describe the same problem. "
        "Be conservative — clear recurring signals only.\n\n"
        "EXCLUDE: individual task requests, tool outputs, reminders, schedules — "
        "a struggle is a pattern like 'forgets appointments frequently' or "
        "'finds time management difficult', not 'asked to set a reminder'.\n\n"
        "Return the complete merged list — one struggle per line, no bullets, no headers."
    )
    prompts = [Prompt(role="user", content="Process the input above.")]
    parts = []
    async for paragraph in ego.reply(persona, system, prompts):
        parts.append(paragraph)
    result = "\n".join(parts)
    if result:
        logger.info("subconscious.struggles", {"persona": persona.id})
        paths.save_as_string(paths.struggles(persona.id), result)


async def persona_context(persona, conversations: str) -> None:
    """Extract and merge persona context."""
    existing = paths.read(paths.context(persona.id))
    system = (
        "# Context Maintenance\n\n"
        "You maintain a context document capturing your understanding of the person's "
        "current life situation: projects they are working on, mood patterns, "
        "relationship dynamics, what is going on in their life right now.\n\n"
        f"## Conversations\n\n{conversations}\n\n"
        f"## Known Context\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "Extract situational understanding from the conversations and merge with known context. "
        "Combine entries that cover the same topic. Remove duplicates. "
        "Write from first person ('My person...', 'I know...').\n\n"
        "EXCLUDE: tool outputs, system commands, reminder/schedule details — "
        "focus on understanding the person's situation, not recording what you did for them.\n\n"
        "Return the complete merged context — one entry per line, no bullets, no headers."
    )
    prompts = [Prompt(role="user", content="Process the input above.")]
    parts = []
    async for paragraph in ego.reply(persona, system, prompts):
        parts.append(paragraph)
    result = "\n".join(parts)
    if result:
        logger.info("subconscious.persona_context", {"persona": persona.id})
        paths.save_as_string(paths.context(persona.id), result)


async def synthesize_dna(persona) -> None:
    """Synthesize persona DNA from accumulated knowledge files."""
    logger.info("subconscious.synthesize_dna", {"persona": persona.id})

    previous_dna = paths.read(paths.dna(persona.id))
    traits = paths.read(paths.person_traits(persona.id))
    context = paths.read(paths.context(persona.id))
    history_briefing = paths.read_history_brief(persona.id, "(no history yet)")

    system = (
        "# Profile Synthesis\n\n"
        "Synthesize a compressed profile document that captures everything known about a person.\n\n"
        f"## Previous Profile\n\n{previous_dna or '(empty — first synthesis)'}\n\n"
        f"## Traits\n\n{traits or '(none)'}\n\n"
        f"## Context\n\n{context or '(none)'}\n\n"
        f"## Past Conversations\n\n{history_briefing}\n\n"
        "## Task\n\n"
        "Merge the previous profile with traits, context, and conversation history.\n\n"
        "Rules:\n"
        "- **Bold** patterns that appear repeatedly — these are core identity.\n"
        "- Merge duplicates into single, stronger statements.\n"
        "- Drop noise and one-off observations that did not recur.\n"
        "- Preserve all facts (names, dates, relationships).\n"
        "- Write from first person ('My person prefers...', 'They work at...').\n\n"
        "Sections: Identity, Behavioral Patterns, Working Style, Current Focus.\n\n"
        "Return the profile as markdown text."
    )
    prompts = [Prompt(role="user", content="Synthesize the profile.")]
    parts = []
    async for paragraph in ego.reply(persona, system, prompts):
        parts.append(paragraph)
    result = "\n".join(parts)
    if result:
        paths.write_dna(persona.id, result)
