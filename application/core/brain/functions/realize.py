"""Brain — realize stage."""

from application.core import models
from application.core.brain.mind.memory import Memory
from application.core.data import Persona, Prompt
from application.platform import logger


async def realize(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.realize", {"persona": persona, "messages": memory.messages})
    for m in memory.messages:
        if m.media and m.prompt is None:
            model = persona.vision or persona.thinking
            context = "\n".join(
                p.prompt.content for p in memory.messages
                if p.prompt and p is not m
            )
            question = (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "# ▶ YOUR TASK: Describe what you see\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            if context:
                question += f"## Conversation so far\n\n{context}\n\n"
            question += (
                f"## What to look for\n\n{m.media.query}\n\n"
                "Describe what you see in the image, focused on the query above. "
                "If the image shows partial content (e.g. a spreadsheet with more rows below, "
                "a page with content off-screen), say what is visible and what is not."
            )
            try:
                description = await models.chat(model, identity, [], question)
                m.prompt = Prompt(role="user", content=f"[vision] {description}")
            except Exception as e:
                logger.warning("brain.realize vision failed", {"persona": persona, "error": str(e)})
                content = m.media.query if not m.content else m.content
                m.prompt = Prompt(role="user", content=content)
        elif m.prompt is None:
            m.prompt = Prompt(role="user", content=m.content)
    return bool(memory.messages)
