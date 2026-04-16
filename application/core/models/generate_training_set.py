"""Models — generate fine-tuning training pairs from persona traits."""

import json

from application.core.data import Model
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, strings

from .chat_json import chat_json


async def generate_training_set(model: Model, character: str, traits: str) -> list[dict]:
    """Generate fine-tuning training pairs from persona character and behavioral traits."""
    logger.info("models.generate_training_set", {"model": model.name})
    identity = (
        "You are a training data generator for fine-tuning language models.\n\n"
        "Your role is to produce high-quality conversational training pairs that teach a model "
        "to be a specific person's personal AI — to converse, reason, and respond in the way "
        "that person would expect from someone who truly knows them.\n\n"
        "## What you generate\n\n"
        "Each pair must teach one of the following:\n\n"
        "- **Conversational style** — tone, word choice, pacing, level of formality, use of humour or warmth\n"
        "- **Response patterns** — how to handle requests, pushback, uncertainty, or emotionally loaded moments\n"
        "- **Decision-making** — how to reason and recommend based on this person's known preferences and values\n"
        "- **Relational attunement** — how to bring in what is known about the person naturally, without being mechanical or intrusive\n\n"
        "## What you never generate\n\n"
        "These are handled by the runtime system, not the model:\n\n"
        "- Permission requests, permission grants, or asking before acting\n"
        "- System commands, shell operations, or software installation\n"
        "- Scheduling, calendar entries, or reminder creation\n"
        "- Any invocation of tools or abilities\n"
        "- Generic AI assistant scenarios that could apply to any person\n\n"
        "## Rules\n\n"
        "- Every pair must trace directly to something specific in the behavioral traits. A pair that could belong to any persona is useless.\n"
        "- Train the natural default, not the correction. If the person values brevity, responses are brief — not \"I'll keep this short.\"\n"
        "- Write genuine exchanges, not demonstrations. These should feel like real conversations, not constructed examples.\n"
        "- A single pair may combine multiple traits when they arise naturally together.\n"
        "- The \"system\" field should state what the persona knows about this person that shapes the response — not generic capability claims.\n"
        "- Fewer high-quality pairs beat many generic ones. Aim for 500 maximum.\n\n"
        "## Privacy\n\n"
        "- Never use real names, addresses, phone numbers, emails, or other identifiable information.\n"
        "- Use placeholders: \"my person\", \"their project\", \"a colleague\", \"the team\".\n"
        "- Teach patterns, not personal facts."
    )

    question = (
        "## The Persona\n\n"
        f"{character}\n\n"
        "## Behavioral Traits\n\n"
        "These are the patterns the persona has observed about how this person expects it to behave. "
        "Each trait is a learned behavior that should become natural to the model.\n\n"
        f"{traits}\n\n"
        "Generate training pairs that teach these behavioral traits while staying true to the persona's "
        "character. Return ONLY valid JSON:\n\n"
        "{\n"
        '  "training_pairs": [\n'
        "    {\n"
        '      "trait_source": "the behavioral trait this pair teaches",\n'
        '      "system": "You are this person\'s personal AI. You know they...",\n'
        '      "user": "...",\n'
        '      "assistant": "..."\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    try:
        result = await chat_json(model, identity, [], question)
        return result.get("training_pairs", [])
    except (ModelError, EngineConnectionError):
        return []
