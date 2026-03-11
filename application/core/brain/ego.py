"""Ego — the persona's reasoning and reply engine."""

from application.core.data import Persona, Prompt
from application.core.brain import character, current
from application.core import local_model
from application.platform import logger


def effect(persona: Persona) -> str:
    """Build the character system prompt for this persona."""
    return character.shape(persona) + "\n\n" + current.situation(persona)


async def reason(persona: Persona, system: str, prompts: list[Prompt]) -> dict:
    """Call the persona's model in JSON mode. Returns a parsed JSON dict."""
    logger.info("ego.reason", {"persona": persona.id})
    full_system = effect(persona) + "\n\n" + system + "\n\nReturn your response as a JSON object."
    messages = [{"role": "system", "content": full_system}]
    messages += [{"role": p.role, "content": p.content} for p in prompts]
    return await local_model.chat_json_stream(persona.model.name, messages)


async def reply(persona: Persona, system: str, prompts: list[Prompt]):
    """Stream the persona's reply, yielding one paragraph at a time."""
    logger.info("ego.reply", {"persona": persona.id})
    full_system = effect(persona) + "\n\n" + system
    messages = [{"role": "system", "content": full_system}]
    messages += [{"role": p.role, "content": p.content} for p in prompts]
    async for paragraph in local_model.chat_stream_paragraph(persona.model.name, messages):
        yield paragraph
