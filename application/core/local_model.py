"""Local model — communicating with the local model."""

import json
from urllib.error import URLError

from application.platform import logger, ollama, strings, OS
from application.core import prompts
from application.core.data import Observation, Persona
from application.core.exceptions import EngineConnectionError


async def observe(
    model: str,
    conversations: str,
    person_identity: str = "",
    person_traits: str = "",
    persona_context: str = "",
    person_struggles: str = "",
) -> Observation:
    """Analyze conversations and extract observations about the person."""
    logger.info("Observing conversations", {"model": model})
    try:
        response = ollama.post("/api/generate", {
            "model": model,
            "prompt": prompts.extraction(
                conversations=conversations,
                person_identity=person_identity,
                person_traits=person_traits,
                persona_context=persona_context,
                person_struggles=person_struggles,
            ),
            "stream": False,
        })
        parsed = strings.extract_json(response["response"])
        return Observation(
            facts=parsed.get("facts", []),
            traits=parsed.get("traits", []),
            context=parsed.get("context", []),
            struggles=parsed.get("struggles", []),
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
            "prompt": prompts.extraction_from_dna(dna=dna),
            "stream": False,
        })
        parsed = strings.extract_json(response["response"])
        return Observation(
            facts=parsed.get("facts", []),
            traits=parsed.get("traits", []),
            context=parsed.get("context", []),
            struggles=[],
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
            "prompt": prompts.skill_assessment(skill_name, skill_content),
            "stream": False,
        })
        parsed = strings.extract_json(response["response"])
        return Observation(
            facts=[],
            traits=parsed.get("traits", []),
            context=parsed.get("context", []),
            struggles=[],
        )
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except (json.JSONDecodeError, KeyError) as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def respond(model: str, messages: list[dict], json_mode: bool = False) -> str:
    """Send a list of messages to the local model and return the response text."""
    logger.info("Generating response", {"model": model})
    try:
        current_os = OS.get_supported()
        if current_os:
            messages = [{"role": "system", "content": f"When running tools, commands must be for {current_os}."}] + messages

        body = {"model": model, "messages": messages, "stream": False}
        if json_mode:
            body["format"] = "json"
        response = ollama.post("/api/chat", body)
        return response["message"]["content"]
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def summarize_thread(model: str, messages: list[dict]) -> dict:
    """Generate a title and one-sentence summary for a conversation thread."""
    logger.info("Summarizing thread", {"model": model})
    try:
        response = ollama.post("/api/generate", {
            "model": model,
            "prompt": prompts.thread_summary(messages),
            "stream": False,
        })
        parsed = strings.extract_json(response["response"])
        return {
            "title": parsed.get("title", "conversation"),
            "summary": parsed.get("summary", ""),
        }
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except (json.JSONDecodeError, KeyError):
        return {"title": "conversation", "summary": ""}


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
