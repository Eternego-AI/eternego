"""Inference config — local inference engine settings."""

import os

import config  # ensures .env is loaded

OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
ANTHROPIC_BASE_URL: str = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
OPENAI_BASE_URL: str = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")
