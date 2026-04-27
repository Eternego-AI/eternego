"""Ability — look_at.

Examine an image file and answer a question about it. Routes through the
persona's eye (vision model) — required, gated by `requires`.
"""

from pathlib import Path

from application.core import models
from application.core.abilities import ability
from application.core.data import Prompt
from application.platform import filesystem, logger


@ability(
    "Examine an image file and answer a question about what's in it. Provide a path to the image and an optional question.",
    requires=lambda persona: persona.vision is not None,
)
async def look_at(persona, source: str = "", question: str = "") -> str:
    logger.debug("ability.look_at", {"persona": persona, "source": source, "question": question})
    if not source:
        raise ValueError("source is required")
    image_path = Path(source)
    if not image_path.exists():
        raise ValueError(f"image not found at {source}")

    # Local import: agents.py imports abilities at module top, so importing
    # Eye at function body time avoids the load-order cycle.
    from application.core.agents import Eye

    image_data = filesystem.read_base64(image_path)
    media_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    image_prompt = Prompt(role="user", content=[
        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
    ])
    eye = Eye(persona)
    return await models.chat(eye.model, eye.identity + [image_prompt], question or "Describe what you see.")
