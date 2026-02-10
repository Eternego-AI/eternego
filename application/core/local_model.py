"""Local model — communicating with the local model."""

from urllib.error import URLError

from application.platform import logger, ollama
from application.core.data import Persona
from application.core.exceptions import EngineConnectionError


async def generate_encryption_phrase(persona: Persona) -> str:
    """Ask the local model to generate a recovery phrase."""
    logger.info("Generating encryption phrase", {"persona_id": persona.id, "model": persona.model.name})
    try:
        response = ollama.post("/api/generate", {
            "model": persona.model.name,
            "prompt": "Generate a 24-word recovery phrase using random common English words. Return only the 24 words separated by spaces, nothing else.",
            "stream": False,
        })
        return response["response"].strip()
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
