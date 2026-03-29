"""Subconscious — sleep-time knowledge extraction.

Each function receives (persona, messages), where messages is a list of
role-based conversation dicts. The system prompt tells the model what to
extract; the messages show the actual conversation.
"""

from application.core import local_model, paths
from application.platform import logger


async def person_identity(persona, messages: list[dict]) -> None:
    """Extract and merge identity facts."""
    logger.debug("subconscious.person_identity", {"persona": persona, "messages": messages})
    existing = paths.read(paths.person_identity(persona.id))
    system = (
        "# Extract Person's Identity Facts\n\n"
        "Read the conversation below. Extract concrete facts about the person.\n\n"
        "What counts:\n"
        "- Name, age, birthday, gender\n"
        "- Where they live, their timezone\n"
        "- Job, employer, profession\n"
        "- Family: spouse, children, parents\n"
        "- Important contacts: doctors, close friends (include name, phone, address when given)\n"
        "- Strong long-term preferences they stated clearly\n\n"
        "Identity data should be relatively permanent and factual."
        "Only extract from what the person said (user messages).\n\n"
        f"## Current Facts\n\n{existing or '(none yet)'}\n\n"
        "Merge new facts into the list above. Keep everything that is still true. "
        "If the conversation adds nothing new, return the current facts unchanged.\n\n"
        "Format: one fact per line, each starting with 'The person '. "
        "No bullets, no headers, no commentary."
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    paths.save_as_string(paths.person_identity(persona.id), result.strip())


async def person_traits(persona, messages: list[dict]) -> None:
    """Extract and merge behavioral traits."""
    logger.debug("subconscious.person_traits", {"persona": persona, "messages": messages})
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
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    paths.save_as_string(paths.person_traits(persona.id), result.strip())


async def wishes(persona, messages: list[dict]) -> None:
    """Extract and merge wishes and aspirations."""
    logger.debug("subconscious.wishes", {"persona": persona, "messages": messages})
    existing = paths.read(paths.wishes(persona.id))
    system = (
        "# Extract Person's Wishes and Dreams\n\n"
        "Read the conversation below. Extract what the person wants in life — "
        "their goals, dreams, and things they care deeply about.\n\n"
        "What counts:\n"
        "- Goals they mentioned: career, personal, creative\n"
        "- Things they said they want to build, achieve, or change\n"
        "- Values they expressed with conviction\n"
        "- Directions they are clearly moving toward\n\n"
        "Wishes are things the person aspires to or deeply cares about. "
        "They may be long-term or short-term, but they indicate what the person wants in life. "
        "Only extract from what the person said (user messages).\n\n"
        f"## Current Wishes\n\n{existing or '(none yet)'}\n\n"
        "Merge new wishes into the list above. Keep everything that is still true. "
        "If the conversation adds nothing new, return the current wishes unchanged.\n\n"
        "Format: one wish per line, each starting with 'The person '. "
        "No bullets, no headers, no commentary."
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    paths.save_as_string(paths.wishes(persona.id), result.strip())


async def struggles(persona, messages: list[dict]) -> None:
    """Extract and merge struggles."""
    logger.debug("subconscious.struggles", {"persona": persona, "messages": messages})
    existing = paths.read(paths.struggles(persona.id))
    system = (
        "# Extract Person's Struggles\n\n"
        "Read the conversation below. Extract difficulties or frustrations the person mentioned.\n\n"
        "What counts:\n"
        "- Problems they described clearly\n"
        "- Things that stress or frustrate them\n"
        "- Obstacles they are facing right now\n"
        "- Anything they said is hard for them\n\n"
        "Struggles are things the person is currently finding difficult. "
        "Only extract from what the person said (user messages).\n\n"
        f"## Current Struggles\n\n{existing or '(none yet)'}\n\n"
        "Merge new struggles into the list above. Keep everything that is still true. "
        "If the conversation adds nothing new, return the current struggles unchanged.\n\n"
        "Format: one struggle per line, each starting with 'The person '. "
        "No bullets, no headers, no commentary."
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    paths.save_as_string(paths.struggles(persona.id), result.strip())


async def persona_trait(persona, messages: list[dict]) -> None:
    """Extract and merge persona behavioral instructions."""
    logger.debug("subconscious.persona_trait", {"persona": persona})
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
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}] + messages)
    paths.save_as_string(paths.persona_trait(persona.id), result.strip())


async def synthesize_dna(persona) -> None:
    """Synthesize persona DNA from persona trait — used for fine-tuning."""
    logger.debug("subconscious.synthesize_dna", {"persona": persona})

    previous_dna = paths.read(paths.dna(persona.id))
    persona_trait_text = paths.read(paths.persona_trait(persona.id))

    system = (
        "# Synthesize Training Profile\n\n"
        "Compress the persona's behavioral instructions into a training profile.\n"
        "This profile will be used to generate fine-tuning data, so it must capture "
        "how the persona should behave — not what happened in conversations.\n\n"
        f"## Previous Profile\n\n{previous_dna or '(first synthesis)'}\n\n"
        f"## Persona Behavioral Instructions\n\n{persona_trait_text or '(none yet)'}\n\n"
        "Bold patterns that appear repeatedly. Merge duplicates. Drop one-off noise.\n"
        "Write as behavioral instructions: 'Be concise', 'Use humor when appropriate'.\n\n"
        "Sections: Communication Style, Working Style, Technical Preferences, Relational Style.\n"
        "Return markdown text."
    )
    result = await local_model.chat(persona.model.name, [{"role": "system", "content": system}, {"role": "user", "content": "Synthesize the training profile."}])
    paths.write_dna(persona.id, result.strip())
