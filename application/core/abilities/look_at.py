"""Ability — look_at.

Queue an image for the eye to look at. Returns a `Media` carrying the
persona's question; the clock executor adds it to memory and realize
processes it on the next cycle, where the eye actually runs and the
answer becomes a `tools.vision` tool-result.

The eye itself lives behind realize — this ability never talks to it
directly. That way every image the persona sees travels the same path:
captured / received → realize → eye → text in memory.
"""

from pathlib import Path

from application.core.abilities import ability
from application.core.data import Media
from application.platform import logger


@ability(
    "Ask your eye about an image file. Provide a path to the image and a "
    "question. The eye's answer arrives on the next cycle as a vision "
    "tool-result you can read in memory."
)
async def look_at(living, source: str = "", question: str = "") -> Media:
    persona = living.ego.persona
    logger.debug("ability.look_at", {"persona": persona, "source": source, "question": question})
    if not source:
        raise ValueError("source is required")
    image_path = Path(source)
    if not image_path.exists():
        raise ValueError(f"image not found at {source}")
    return Media(
        source=str(image_path),
        caption="look_at done",
        question=question or "Describe what you see.",
    )
