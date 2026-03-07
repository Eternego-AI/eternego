"""Local model — communicating with the local model."""

import json

from application.platform import logger, ollama, strings, OS
from application.core.exceptions import EngineConnectionError


async def chat(model: str, messages: list[dict], json_mode: bool = False) -> str:
    """Send a list of messages to the local model and return the response text."""
    logger.info("Sending chat request to model", {"model": model})
    try:
        current_os = OS.get_supported()
        if current_os:
            messages = [{"role": "system", "content": f"When running tools, commands must be for {current_os}."}] + messages

        body = {"model": model, "messages": messages, "stream": False}
        if json_mode:
            body["format"] = "json"
        response = await ollama.post("/api/chat", body)
        return response["message"]["content"]
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except KeyError as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def chat_json(model: str, messages: list[dict]) -> dict:
    """Send a list of messages to the local model and return the parsed JSON response."""
    logger.info("Sending JSON chat request to model", {"model": model})
    response = await chat(model, messages, json_mode=True)
    try:
        return strings.extract_json(response)
    except json.JSONDecodeError as e:
        raise EngineConnectionError("Model returned an invalid JSON response") from e


async def stream_chat(model: str, messages: list[dict], json_mode: bool = False) -> str:
    """Stream a chat request and return the assembled response text.

    Uses streaming so Ollama aborts generation if the connection closes mid-tick.
    """
    logger.info("Streaming chat request to model", {"model": model})
    try:
        current_os = OS.get_supported()
        if current_os:
            messages = [{"role": "system", "content": f"When running tools, commands must be for {current_os}."}] + messages

        body = {"model": model, "messages": messages}
        if json_mode:
            body["format"] = "json"
        parts = []
        async for chunk in ollama.stream_post("/api/chat", body):
            parts.append(chunk.get("message", {}).get("content", ""))
        return "".join(parts)
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def stream_chat_json(model: str, messages: list[dict]) -> dict:
    """Stream a chat request and return the parsed JSON response."""
    logger.info("Streaming JSON chat request to model", {"model": model})
    response = await stream_chat(model, messages, json_mode=True)
    try:
        return strings.extract_json(response)
    except json.JSONDecodeError as e:
        raise EngineConnectionError("Model returned an invalid JSON response") from e


async def generate(model: str, prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to the local model and return the response text."""
    logger.info("Sending generate request to model", {"model": model, "prompt": prompt})
    try:
        body = {"model": model, "prompt": prompt, "stream": False}
        if json_mode:
            body["format"] = "json"
        response = await ollama.post("/api/generate", body)
        return response["response"].strip()
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except KeyError as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def generate_json(model: str, prompt: str) -> dict:
    """Send a prompt to the local model and return the parsed JSON response."""
    logger.info("Sending JSON generate request to model", {"model": model, "prompt": prompt})
    response = await generate(model, prompt, json_mode=True)
    try:
        return strings.extract_json(response)
    except json.JSONDecodeError as e:
        raise EngineConnectionError("Model returned an invalid JSON response") from e
