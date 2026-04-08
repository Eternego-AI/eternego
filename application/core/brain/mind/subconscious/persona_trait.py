"""Subconscious — derive persona behavioral instructions."""

from application.core import models, paths
from application.platform import logger


async def persona_trait(persona, conversation: str) -> None:
    """Extract and merge persona behavioral instructions."""
    logger.debug("subconscious.persona_trait", {"persona": persona, "conversation": conversation})
    existing = paths.read(paths.persona_trait(persona.id))
    person_traits_text = paths.read(paths.person_traits(persona.id))
    system = (
        "# Derive Persona Behavioral Instructions\n\n"
        "You are observing how a person communicates and what they expect. "
        "From this, derive instructions for how YOU (the persona) should behave.\n\n"
        f"## Person's Observed Traits\n\n{person_traits_text or '(none yet)'}\n\n"
        "## What to extract\n\n"
        "Behavioral instructions for yourself based on what you observe:\n"
        "- Communication style to match: humor, formality, directness, brevity\n"
        "- Technical preferences: languages, frameworks, methodologies they use\n"
        "- Working style: do they want options or decisions? details or summaries?\n"
        "- How to challenge or support them based on their patterns\n\n"
        "Person trait observes ('the person is concise'). "
        "Persona trait instructs ('be concise'). "
        "Do NOT include facts about the person (name, job). "
        "Do NOT include their wishes or struggles. "
        "Only derive behavioral instructions from the conversation and traits.\n\n"
        f"## Current Instructions\n\n{existing or '(none yet)'}\n\n"
        "Merge new instructions into the list above. Keep what is still valid. "
        "If the conversation adds nothing new, return the current instructions unchanged.\n\n"
        "Format: one instruction per line, written as an imperative ('Be concise', 'Use humor', "
        "'Match their direct style'). No bullets, no headers, no commentary."
    )
    result = await models.chat(persona.thinking, [{"role": "system", "content": system}, {"role": "user", "content": conversation}])
    paths.save_as_string(paths.persona_trait(persona.id), result.strip())
