"""Web config — host and port for the FastAPI server."""

import os

import config  # ensures .env is loaded

HOST: str = os.environ.get("WEB_HOST", "127.0.0.1")
PORT: int = int(os.environ.get("WEB_PORT", "5000"))
