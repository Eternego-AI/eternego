"""Local model — communicating with the local model."""

import json

from application.platform import logger, ollama, strings, OS
from application.core.exceptions import EngineConnectionError


async def chat(model: str, messages: list[dict]) -> str:
    """Send messages, wait for full response."""
    logger.info("local_model.chat", {"model": model})
    try:
        current_os = OS.get_supported()
        if current_os:
            messages = [{"role": "system", "content": f"When running tools, commands must be for {current_os}."}] + messages
        response = await ollama.post("/api/chat", {"model": model, "messages": messages, "stream": False})
        return response["message"]["content"]
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except KeyError as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def chat_json(model: str, messages: list[dict]) -> dict:
    """Send messages, wait for full JSON response."""
    logger.info("local_model.chat_json", {"model": model})
    try:
        current_os = OS.get_supported()
        if current_os:
            messages = [{"role": "system", "content": f"When running tools, commands must be for {current_os}."}] + messages
        response = await ollama.post("/api/chat", {"model": model, "messages": messages, "stream": False, "format": "json"})
        return strings.extract_json(response["message"]["content"])
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except (KeyError, json.JSONDecodeError) as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def chat_stream(model: str, messages: list[dict]):
    """Stream response, yielding one token at a time."""
    logger.info("local_model.chat_stream", {"model": model})
    try:
        async for chunk in ollama.stream_post("/api/chat", {"model": model, "messages": messages}):
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def chat_json_stream(model: str, messages: list[dict]) -> dict:
    """Stream response, collect and return parsed JSON."""
    logger.info("local_model.chat_json_stream", {"model": model})
    try:
        body = {"model": model, "messages": messages, "format": "json"}
        parts = []
        async for chunk in ollama.stream_post("/api/chat", body):
            parts.append(chunk.get("message", {}).get("content", ""))
        return strings.extract_json("".join(parts))
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except json.JSONDecodeError as e:
        raise EngineConnectionError("Model returned an invalid JSON response") from e


async def chat_stream_paragraph(model: str, messages: list[dict]):
    """Stream response, yielding one complete line at a time."""
    logger.info("local_model.chat_stream_paragraph", {"model": model})
    buffer = ""
    async for token in chat_stream(model, messages):
        buffer += token
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line.strip():
                yield line.strip()
    if buffer.strip():
        yield buffer.strip()


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
