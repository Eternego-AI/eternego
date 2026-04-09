"""Subconscious — extract and merge behavioral traits."""

from application.core import models, paths
from application.platform import logger


async def person_traits(persona, conversation: str) -> None:
    """Extract and merge behavioral traits."""
    logger.debug("subconscious.person_traits", {"persona": persona, "conversation": conversation})
    existing = paths.read(paths.person_traits(persona.id))
    system = (
        "# Extract Person's Behavioral Traits\n\n"
        "Read the conversation below. Extract how the person communicates and what style they prefer.\n\n"
        "What counts:\n"
        "- Short or long messages? Formal or casual?\n"
        "- Do they use humor? Emojis? Are they direct or roundabout?\n"
        "- Do they want details or just the answer?\n"
        "- Any clear preference they showed in how they want to be talked to\n\n"
        "Traits are patterns in how the person communicates and what they prefer in interactions. "
        "They are not facts about their identity, but rather tendencies or styles. "
        "Only extract from what the person said (user messages). "
        f"## Current Traits\n\n{existing or '(none yet)'}\n\n"
        "Merge new traits into the list above. Keep everything that is still true. "
        "If the conversation adds nothing new, return the current traits unchanged.\n\n"
        "Format: one trait per line, each starting with 'The person '. "
        "No bullets, no headers, no commentary."
    )
    result = await models.chat(persona.thinking, [{"role": "system", "content": system}, {"role": "user", "content": conversation}])
    paths.save_as_string(paths.person_traits(persona.id), result.strip())
