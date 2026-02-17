"""Local model — communicating with the local model."""

import json
from collections.abc import AsyncIterator
from urllib.error import URLError

from application.platform import logger, ollama, OS
from application.core import prompts
from application.core.data import Observation, Persona
from application.core.exceptions import EngineConnectionError


async def observe(model: str, conversations: str) -> Observation:
    """Analyze conversations and extract observations about the person."""
    logger.info("Observing conversations", {"model": model})
    try:
        response = ollama.post("/api/generate", {
            "model": model,
            "prompt": prompts.EXTRACTION.format(conversations=conversations),
            "stream": False,
        })
        parsed = json.loads(response["response"])
        return Observation(
            facts=parsed.get("facts", []),
            traits=parsed.get("traits", []),
            context=parsed.get("context", []),
        )
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except (json.JSONDecodeError, KeyError) as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def study(model: str, dna: str) -> Observation:
    """Study DNA and extract observations to populate traits and context."""
    logger.info("Studying DNA", {"model": model})
    try:
        response = ollama.post("/api/generate", {
            "model": model,
            "prompt": prompts.EXTRACTION.format(conversations=dna),
            "stream": False,
        })
        parsed = json.loads(response["response"])
        return Observation(
            facts=parsed.get("facts", []),
            traits=parsed.get("traits", []),
            context=parsed.get("context", []),
        )
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except (json.JSONDecodeError, KeyError) as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def assess_skill(model: str, skill_name: str, skill_content: str) -> Observation:
    """Analyze a skill document and extract observations using the given model."""
    logger.info("Assessing skill", {"model": model, "skill": skill_name})
    try:
        response = ollama.post("/api/generate", {
            "model": model,
            "prompt": prompts.SKILL_ASSESSMENT.format(
                skill_name=skill_name,
                skill_content=skill_content,
            ),
            "stream": False,
        })
        parsed = json.loads(response["response"])
        return Observation(
            facts=[],
            traits=parsed.get("traits", []),
            context=parsed.get("context", []),
        )
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except (json.JSONDecodeError, KeyError) as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def stream(model: str, messages: list[dict]) -> AsyncIterator[dict]:
    """Stream a chat response from the local model, yielding raw Ollama responses."""
    logger.info("Streaming response", {"model": model})
    try:
        current_os = OS.get_supported()
        if current_os:
            messages = [{"role": "system", "content": f"When running tools, commands must be for {current_os}."}] + messages

        for raw in ollama.stream_post("/api/chat", {
            "model": model,
            "messages": messages,
            "stream": True,
        }):
            yield raw
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def respond(model: str, prompt: str) -> str:
    """Send a prompt to the local model and return the response text."""
    logger.info("Generating response", {"model": model})
    try:
        response = ollama.post("/api/generate", {
            "model": model,
            "prompt": prompt,
            "stream": False,
        })
        return response["response"]
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def generate_encryption_phrase(persona: Persona) -> str:
    """Ask the local model to generate a recovery phrase."""
    logger.info("Generating encryption phrase", {"persona_id": persona.id, "model": persona.model.name})
    try:
        response = ollama.post("/api/generate", {
            "model": persona.model.name,
            "prompt": prompts.RECOVERY_PHRASE,
            "stream": False,
        })
        return response["response"].strip()
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
