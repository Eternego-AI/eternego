"""Frontier — escalation to a more powerful external model."""

import asyncio, json
from urllib.error import URLError

from application.platform import logger
from application.platform import anthropic
from application.platform import openai
from application.core.data import Model
from application.core.exceptions import FrontierError


async def chat(model: Model, prompt: str) -> str:
    """Send a prompt to a frontier model and return the response."""
    logger.info("Responding via frontier", {"model": model.name})
    messages = [{"role": "user", "content": prompt}]
    creds = model.credentials or {}
    provider = model.provider or "openai"
    api_key = creds.get("api_key", "")

    try:
        if provider == "openai":
            return await asyncio.to_thread(openai.chat, api_key, model.name, messages)
        if provider == "anthropic":
            return await asyncio.to_thread(anthropic.chat, api_key, model.name, messages)
        raise FrontierError(f"Unsupported frontier provider: {provider}")
    except (URLError, OSError) as e:
        raise FrontierError(f"Failed to contact frontier model: {e}") from e


async def chat_json(model: Model, prompt: str) -> dict:
    """Send a prompt to a frontier model and return the parsed JSON response."""
    logger.info("Responding with JSON via frontier", {"model": model.name})
    messages = [{"role": "user", "content": prompt}]
    creds = model.credentials or {}
    provider = model.provider or "openai"
    api_key = creds.get("api_key", "")

    try:
        if provider == "openai":
            return await asyncio.to_thread(openai.chat_json, api_key, model.name, messages)
        if provider == "anthropic":
            return await asyncio.to_thread(anthropic.chat_json, api_key, model.name, messages)
        raise FrontierError(f"Unsupported frontier provider: {provider}")
    except (URLError, OSError) as e:
        raise FrontierError(f"Failed to contact frontier model: {e}") from e


async def generate_training_set(model: Model, dna: str) -> list[dict]:
    """Generate fine-tuning training pairs from persona DNA using a frontier model."""
    logger.info("frontier.generate_training_set", {"model": model.name})
    prompt = (
        "# Training Data Generation\n\n"
        "You are generating fine-tuning examples that teach a language model to be a specific person's personal AI —\n"
        "to converse, reason, and respond in the way that person would expect from someone who truly knows them.\n\n"
        "## Person Profile\n\n"
        f"{dna}\n\n"
        "**Bolded** patterns are recurring and core to this person's identity — weight these most heavily.\n\n"
        "## What to Generate\n\n"
        "Each pair must teach one of the following:\n\n"
        "- **Conversational style** — tone, word choice, pacing, level of formality, use of humour or warmth\n"
        "- **Response patterns** — how to handle requests, pushback, uncertainty, or emotionally loaded moments\n"
        "- **Decision-making** — how to reason and recommend based on this person's known preferences and values\n"
        "- **Relational attunement** — how to bring in what is known about the person naturally, without being mechanical or intrusive\n\n"
        "## What NOT to Generate\n\n"
        "Do not generate pairs involving any of the following — these are handled by the runtime system, not the model:\n\n"
        "- Permission requests, permission grants, or asking before acting\n"
        "- System commands, shell operations, or software installation\n"
        "- Scheduling, calendar entries, or reminder creation\n"
        "- Any invocation of tools or abilities\n"
        "- Generic AI assistant scenarios that could apply to any person\n\n"
        "## Rules\n\n"
        "- Every pair must trace directly to something specific in the profile. A pair that could belong to any persona is useless.\n"
        "- Train the natural default, not the correction. If the person values brevity, responses are brief — not \"I'll keep this short.\"\n"
        "- Write genuine exchanges, not demonstrations. These should feel like real conversations, not constructed examples.\n"
        "- A single pair may combine multiple traits when they arise naturally together.\n"
        "- The \"system\" field should state what the persona knows about this person that shapes the response — not generic capability claims.\n"
        "- Fewer high-quality pairs beat many generic ones. Aim for 500 maximum.\n\n"
        "## Privacy\n\n"
        "- Never use real names, addresses, phone numbers, emails, or other identifiable information.\n"
        "- Use placeholders: \"my person\", \"their project\", \"a colleague\", \"the team\".\n"
        "- Teach patterns, not personal facts.\n\n"
        "## Output\n\n"
        "Return ONLY valid JSON:\n\n"
        "{\n"
        '  "training_pairs": [\n'
        "    {\n"
        '      "trait_source": "the DNA trait this pair teaches",\n'
        '      "system": "You are this person\'s personal AI. You know they...",\n'
        '      "user": "...",\n'
        '      "assistant": "..."\n'
        "    }\n"
        "  ]\n"
        "}"
    )
    response = await chat(model, prompt)
    try:
        parsed = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed.get("training_pairs", [])


async def read(data: str, source: str) -> list[dict]:
    """Parse external AI history into role-based messages."""
    logger.info("Reading external LLM history", {"source": source})
    try:
        if source == "claude":
            return anthropic.to_messages(data)

        return openai.to_messages(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise FrontierError("Could not parse external data") from e

