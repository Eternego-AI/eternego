"""Ollama — local model communication: serve, pull, generate, model management."""

import json

import httpx

from config.inference import OLLAMA_BASE_URL


class Client:
    """Ollama API client wrapping the HTTP transport."""

    def __init__(self):
        self._http = httpx.AsyncClient(
            base_url=OLLAMA_BASE_URL,
            timeout=httpx.Timeout(None, connect=10.0),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self._http.aclose()


def connect() -> Client:
    """Create an Ollama API client."""
    return Client()


async def is_serving(client: Client) -> bool:
    """Check if the Ollama server is responding."""
    try:
        response = await client._http.get("/")
        return response.status_code == 200
    except httpx.RequestError:
        return False


async def get(client: Client, path: str) -> dict:
    """Send a GET request to the Ollama API."""
    try:
        response = await client._http.get(path)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def post(client: Client, path: str, data: dict) -> dict:
    """Send a POST request to the Ollama API."""
    try:
        response = await client._http.post(path, json=data)
        response.raise_for_status()
        body = response.text.strip()
        return response.json() if body else {}
    except httpx.HTTPStatusError as e:
        raise ConnectionError(f"Ollama API error {e.response.status_code}: {e.response.text}") from e
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def delete(client: Client, path: str, data: dict) -> dict:
    """Send a DELETE request to the Ollama API."""
    try:
        response = await client._http.request("DELETE", path, json=data)
        response.raise_for_status()
        body = response.text.strip()
        return response.json() if body else {}
    except httpx.RequestError as e:
        raise ConnectionError(f"Could not reach Ollama: {e}") from e


async def stream(client: Client, path: str, data: dict):
    """Send a POST request and yield JSON chunks as they arrive."""
    async with client._http.stream("POST", path, json=data) as response:
        async for line in response.aiter_lines():
            if line.strip():
                yield json.loads(line)
