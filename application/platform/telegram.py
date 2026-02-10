"""Telegram — Telegram Bot API communication."""

import json
import urllib.request


BASE_URL = "https://api.telegram.org"


async def send(token: str, chat_id: str, message: str) -> dict:
    """Send a message via Telegram Bot API."""
    request = urllib.request.Request(
        f"{BASE_URL}/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": message}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())
