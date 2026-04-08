"""Subconscious — synthesize persona DNA for fine-tuning."""

from application.core import models, paths
from application.platform import logger


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
    result = await models.chat(persona.thinking, [{"role": "system", "content": system}, {"role": "user", "content": "Synthesize the training profile."}])
    paths.save_as_string(paths.dna(persona.id), result.strip())
