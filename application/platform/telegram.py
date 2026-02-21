"""Telegram — Telegram Bot API communication."""

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable


BASE_URL = "https://api.telegram.org"

POLL_INTERVAL = 1
POLL_TIMEOUT = 30


def get_me(token: str) -> dict:
    """Validate a bot token via getMe. Returns bot info dict."""
    request = urllib.request.Request(
        f"{BASE_URL}/bot{token}/getMe",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def send(token: str, chat_id: str, message: str) -> dict:
    """Send a message via Telegram Bot API."""
    request = urllib.request.Request(
        f"{BASE_URL}/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": message}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def typing_action(token: str, chat_id: str) -> None:
    """Send a typing indicator to a Telegram chat."""
    request = urllib.request.Request(
        f"{BASE_URL}/bot{token}/sendChatAction",
        data=json.dumps({"chat_id": chat_id, "action": "typing"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        json.loads(response.read())


def poll(
    token: str,
    username: str,
    on_message: Callable[[str, str], None],
    stop: Callable[[], bool],
    on_error: Callable[[Exception], None] | None = None,
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

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            if on_error:
                on_error(e)
            time.sleep(POLL_INTERVAL)
            continue

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "")
            msg_chat_id = str(message.get("chat", {}).get("id", ""))

            if not text or not msg_chat_id:
                continue

            is_group = message.get("chat", {}).get("type", "") in ("group", "supergroup")
            if is_group and not is_mentioned(username, text):
                continue

            on_message(text, msg_chat_id)


def is_mentioned(username: str, text: str) -> bool:
    """Check if the username is mentioned in the message text."""
    return f"@{username}" in text.lower() or username.lower() in text.lower()
