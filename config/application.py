"""Application config — core application settings."""

import os

import config  # ensures .env is loaded

OPENAI_TIMEOUT: int = int(os.environ.get("OPENAI_TIMEOUT", "30"))
