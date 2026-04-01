"""Inference config — local inference engine settings."""

import os

import config  # ensures .env is loaded

OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
