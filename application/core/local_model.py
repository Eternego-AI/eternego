"""Local model — communicating with the local model."""

import asyncio
import json
from urllib.error import URLError


from application.platform import logger, ollama, strings, OS
from application.core.exceptions import EngineConnectionError

async def request(model: str, prompt: str) -> str:
    """Send a request to the local model and return the response text."""
    logger.info("Sending request to model", {"model": model, "prompt": prompt})
    try:
        response = await asyncio.to_thread(ollama.post, "/api/generate", {
            "model": model,
            "prompt": prompt,
            "stream": False,
        })
        return response["response"].strip()
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except KeyError as e:
        raise EngineConnectionError("Model returned an invalid response") from e



async def request_json(model: str, prompt: str) -> dict:
    """Send a request to the local model and return the parsed JSON response."""
    logger.info("Sending JSON request to model", {"model": model, "prompt": prompt})
    try:
        response = await asyncio.to_thread(ollama.post, "/api/generate", {
            "model": model,
            "prompt": prompt,
            "stream": False,
        })
        return strings.extract_json(response["response"])
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
        response = await asyncio.to_thread(ollama.post, "/api/chat", body)
        return response["message"]["content"]
    except URLError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


