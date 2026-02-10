"""Ollama — local model communication: serve, pull, generate, model management."""

import json
import urllib.request


BASE_URL = "http://localhost:11434"


def get(path: str) -> dict:
    """Send a GET request to the Ollama API."""
    with urllib.request.urlopen(f"{BASE_URL}{path}") as response:
        return json.loads(response.read())


def post(path: str, data: dict) -> dict:
    """Send a POST request to the Ollama API."""
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())
