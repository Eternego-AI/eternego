"""Subconscious — sleep-time knowledge extraction.

Each function receives (persona, messages), where messages is a list of
role-based conversation dicts. The system prompt tells the model what to
extract; the messages show the actual conversation.
"""

from application.core import local_model, paths
from application.platform import logger


async def person_identity(persona, messages: list[dict]) -> None:
    """Extract and merge identity facts."""
    existing = paths.read(paths.person_identity(persona.id))
    system = (
        "# Extract Identity Facts\n\n"
        "Read the conversation and extract stable, long-term facts about the person.\n\n"
        "Look for: name, date of birth, gender, home location, job and employer, "
        "family (spouse, children, parents), important contacts (doctors, close friends — "
        "include name, address, phone when given), timezone, strong long-term preferences.\n\n"
        "Only extract from what the person said (user messages), not from assistant replies.\n\n"
        "Timezone rule: for temporary travel, add date range "
        "(e.g. 'The person's timezone is Asia/Tokyo from March 15 to March 22, 2026'). "
        "Only change home timezone if they say they moved permanently.\n\n"
        f"## Current Facts\n\n{existing or '(none yet)'}\n\n"
        "Merge new facts with current facts. Combine duplicates. On conflict, keep most recent.\n"
        "Only add facts that are stable and lasting — skip moods, plans, opinions, and behavioral style.\n\n"
        "Return the complete merged list. One fact per line, each starting with 'The person '.\n"
        "No bullets, no headers, no commentary. If nothing to report, return: (none yet)"
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    if result:
        logger.debug("subconscious.person_identity", {"persona": persona})
        paths.save_as_string(paths.person_identity(persona.id), result)


async def person_traits(persona, messages: list[dict]) -> None:
    """Extract and merge behavioral traits."""
    existing = paths.read(paths.person_traits(persona.id))
    system = (
        "# Extract Behavioral Traits\n\n"
        "Read the conversation and extract recurring patterns in how the person "
        "communicates and what interaction style they prefer.\n\n"
        "Look for: concise vs verbose, formal vs casual, humor style, "
        "how much detail they want, directness, personality patterns shown repeatedly.\n\n"
        "Only extract from what the person said (user messages), not from assistant replies.\n"
        "Only add patterns that appear repeatedly or are strongly emphasized.\n\n"
        f"## Current Traits\n\n{existing or '(none yet)'}\n\n"
        "Merge with current traits. Combine duplicates. On conflict, keep most recent.\n"
        "Skip identity facts (name, location, job) and one-off statements.\n\n"
        "Return the complete merged list. One trait per line, each starting with 'The person '.\n"
        "No bullets, no headers, no commentary. If nothing to report, return: (none yet)"
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    if result:
        logger.debug("subconscious.person_traits", {"persona": persona})
        paths.save_as_string(paths.person_traits(persona.id), result)


async def wishes(persona, messages: list[dict]) -> None:
    """Extract and merge wishes and aspirations."""
    existing = paths.read(paths.wishes(persona.id))
    system = (
        "# Extract Aspirations\n\n"
        "Read the conversation and extract the person's deeper desires, "
        "long-term dreams, and life direction signals.\n\n"
        "Look for: recurring longings, life goals, career aspirations, "
        "emotional readiness for change, dreams they keep coming back to.\n\n"
        "Only extract from what the person said (user messages), not from assistant replies.\n"
        "These are not tasks or reminders — they are underlying wants and dreams.\n\n"
        f"## Current Aspirations\n\n{existing or '(none yet)'}\n\n"
        "Merge with current aspirations. Combine duplicates. On conflict, keep most recent.\n"
        "Only add entries with emotional weight or repetition.\n\n"
        "Return the complete merged list. One aspiration per line, each starting with 'The person '.\n"
        "No bullets, no headers, no commentary. If nothing to report, return: (none yet)"
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    if result:
        logger.debug("subconscious.wishes", {"persona": persona})
        paths.save_as_string(paths.wishes(persona.id), result)


async def struggles(persona, messages: list[dict]) -> None:
    """Extract and merge recurring struggles."""
    existing = paths.read(paths.struggles(persona.id))
    system = (
        "# Extract Struggles\n\n"
        "Read the conversation and extract recurring personal obstacles "
        "and friction points the person faces.\n\n"
        "Look for: repeated difficulties, avoidance patterns, "
        "consistent sources of stress, procrastination areas, emotional blocks.\n\n"
        "Only extract from what the person said (user messages), not from assistant replies.\n"
        "Only add patterns that recur or carry strong emotional weight — not one-off complaints.\n\n"
        f"## Current Struggles\n\n{existing or '(none yet)'}\n\n"
        "Merge with current struggles. Combine duplicates. On conflict, keep most recent.\n\n"
        "Return the complete merged list. One struggle per line, each starting with 'The person '.\n"
        "No bullets, no headers, no commentary. If nothing to report, return: (none yet)"
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    if result:
        logger.debug("subconscious.struggles", {"persona": persona})
        paths.save_as_string(paths.struggles(persona.id), result)


async def persona_context(persona, messages: list[dict]) -> None:
    """Extract and merge persona context."""
    existing = paths.read(paths.context(persona.id))
    system = (
        "# Extract Life Context\n\n"
        "Read the conversation and extract the person's current life situation — "
        "what chapter they are in right now.\n\n"
        "Look for: active projects, life phase, emotional state, "
        "relationship dynamics, current focus — things that are alive and recent.\n\n"
        "Only extract from what the person said (user messages), not from assistant replies.\n"
        "Skip permanent facts (name, job) and long-term dreams — focus on what is happening now.\n\n"
        f"## Current Context\n\n{existing or '(none yet)'}\n\n"
        "Merge with current context. Remove outdated entries. Keep 4-12 lines max.\n"
        "Write from the persona's perspective: 'I know that...', 'My person...'.\n\n"
        "Return the complete merged snapshot. One statement per line.\n"
        "No bullets, no headers, no commentary.\n"
        "If nothing relevant, return: (light context — mostly quiet season right now)"
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    if result:
        logger.debug("subconscious.persona_context", {"persona": persona})
        paths.save_as_string(paths.context(persona.id), result)


async def synthesize_dna(persona) -> None:
    """Synthesize persona DNA from accumulated knowledge files."""
    logger.debug("subconscious.synthesize_dna", {"persona": persona})

    previous_dna = paths.read(paths.dna(persona.id))
    traits = paths.read(paths.person_traits(persona.id))
    context = paths.read(paths.context(persona.id))
    history_briefing = paths.read_history_brief(persona.id, "(no history yet)")

    system = (
        "# Synthesize Profile\n\n"
        "Merge all data below into a single compressed profile.\n\n"
        f"## Previous Profile\n\n{previous_dna or '(first synthesis)'}\n\n"
        f"## Traits\n\n{traits or '(none)'}\n\n"
        f"## Context\n\n{context or '(none)'}\n\n"
        f"## Past Conversations\n\n{history_briefing}\n\n"
        "Bold patterns that appear repeatedly. Merge duplicates. Drop one-off noise.\n"
        "Preserve all facts (names, dates, relationships).\n"
        "Write as: 'My person prefers...', 'They work at...'.\n\n"
        "Sections: Identity, Behavioral Patterns, Working Style, Current Focus.\n"
        "Return markdown text."
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}, {"role": "user", "content": "Synthesize the profile."}])
    if result:
        paths.write_dna(persona.id, result)
