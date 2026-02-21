"""Pairing — in-memory short-lived codes for verifying incoming channel connections."""

import random
import string
from datetime import datetime, timedelta, timezone

from application.platform import logger

_EXPIRY_MINUTES = 10
_CODE_CHARS = string.ascii_uppercase + string.digits  # 36^6 ≈ 2.1 billion combinations

_pending: dict[str, dict] = {}  # code → {persona_id, network_id, chat_id, created_at}


def _cleanup() -> None:
    """Remove expired codes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=_EXPIRY_MINUTES)
    expired = [code for code, entry in _pending.items() if entry["created_at"] < cutoff]
    for code in expired:
        del _pending[code]


def _unique_code() -> str:
    while True:
        code = "".join(random.choices(_CODE_CHARS, k=6))
        if code not in _pending:
            return code


def generate(persona_id: str, network_id: str, chat_id: str) -> str:
    """Generate a fresh pairing code for an unknown chat_id. Returns the code."""
    logger.info("Generating pairing code", {"persona": persona_id, "network": network_id})
    _cleanup()
    # If this chat_id already has a pending code, reuse it so the user isn't confused
    for code, entry in _pending.items():
        if entry["persona_id"] == persona_id and entry["network_id"] == network_id and entry["chat_id"] == chat_id:
            return code
    code = _unique_code()
    _pending[code] = {
        "persona_id": persona_id,
        "network_id": network_id,
        "chat_id": chat_id,
        "created_at": datetime.now(timezone.utc),
    }
    return code


def claim(code: str) -> dict | None:
    """Claim a pairing code. Returns {persona_id, network_id, chat_id} or None if invalid/expired."""
    logger.info("Claiming pairing code", {"code": code})
    _cleanup()
    entry = _pending.pop(code.upper(), None)
    if entry is None:
        return None
    return {
        "persona_id": entry["persona_id"],
        "network_id": entry["network_id"],
        "chat_id": entry["chat_id"],
    }
