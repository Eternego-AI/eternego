"""Ollama — local model communication: serve, pull, generate, model management."""

import json
import httpx

BASE_URL = "http://localhost:11434"

_client = httpx.AsyncClient(
    base_url=BASE_URL,
    timeout=httpx.Timeout(None, connect=10.0),
)


async def get(path: str) -> dict:
    """Send a GET request to the Ollama API."""
    try:
        response = await _client.get(path)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def post(path: str, data: dict) -> dict:
    """Send a POST request to the Ollama API."""
    try:
        response = await _client.post(path, json=data)
        response.raise_for_status()
        body = response.text.strip()
        return response.json() if body else {}
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def delete(path: str, data: dict) -> dict:
    """Send a DELETE request to the Ollama API."""
    try:
        response = await _client.request("DELETE", path, json=data)
        response.raise_for_status()
        body = response.text.strip()
        return response.json() if body else {}
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def stream_post(path: str, data: dict):
    """Send a POST request and yield JSON chunks as they arrive."""
    async with _client.stream("POST", path, json=data) as response:
        async for line in response.aiter_lines():
            if line.strip():
                yield json.loads(line)
