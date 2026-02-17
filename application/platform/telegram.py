"""Telegram — Telegram Bot API communication."""

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable


BASE_URL = "https://api.telegram.org"

POLL_INTERVAL = 1
POLL_TIMEOUT = 30


def send(token: str, chat_id: str, message: str) -> dict:
    """Send a message via Telegram Bot API."""
    request = urllib.request.Request(
        f"{BASE_URL}/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": message}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def poll(
    token: str,
    chat_id: str,
    username: str,
    on_message: Callable[[str], None],
    stop: Callable[[], bool],
) -> None:
    """Long-poll for incoming messages. Runs in a thread."""
    offset = 0

    while not stop():
        try:
            request = urllib.request.Request(
                f"{BASE_URL}/bot{token}/getUpdates",
                data=json.dumps({"offset": offset, "timeout": POLL_TIMEOUT}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=POLL_TIMEOUT + 5) as response:
                data = json.loads(response.read())

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            time.sleep(POLL_INTERVAL)
            continue

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "")
            msg_chat_id = str(message.get("chat", {}).get("id", ""))

            if msg_chat_id != chat_id:
                continue

            if not text:
                continue

            is_group = message.get("chat", {}).get("type", "") in ("group", "supergroup")
            if is_group and not is_mentioned(username, text):
                continue

            on_message(text)


def is_mentioned(username: str, text: str) -> bool:
    """Check if the username is mentioned in the message text."""
    return f"@{username}" in text.lower() or username.lower() in text.lower()
