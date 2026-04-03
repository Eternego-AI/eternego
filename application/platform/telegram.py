"""Telegram — Telegram Bot API communication."""

import json
import threading
import urllib.error
import urllib.request

from http.server import HTTPServer, BaseHTTPRequestHandler


BASE_URL = "https://api.telegram.org"

POLL_TIMEOUT = 30


def get_me(token: str) -> dict:
    """Validate a bot token via getMe. Returns bot info dict."""
    req = urllib.request.Request(
        f"{BASE_URL}/bot{token}/getMe",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def send(token: str, chat_id: str, message: str) -> dict:
    """Send a message via Telegram Bot API."""
    req = urllib.request.Request(
        f"{BASE_URL}/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": message}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def typing_action(token: str, chat_id: str) -> None:
    """Send a typing indicator to a Telegram chat."""
    req = urllib.request.Request(
        f"{BASE_URL}/bot{token}/sendChatAction",
        data=json.dumps({"chat_id": chat_id, "action": "typing"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        json.loads(response.read())


def direct_or_mentioned_in_group(username: str, updates: list[dict]) -> list[tuple[str, str, str]]:
    """Filter updates to direct messages or group mentions.

    Returns list of (text, chat_id, message_id) tuples.
    """
    results = []
    for update in updates:
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = str(message.get("chat", {}).get("id", ""))

        if not text or not chat_id:
            continue

        msg_id = str(message.get("message_id", ""))

        is_group = message.get("chat", {}).get("type", "") in ("group", "supergroup")
        if is_group and not is_mentioned(username, text):
            continue

        results.append((text, chat_id, msg_id))

    return results


def poll(token: str, offset: int = 0) -> tuple[list[dict], int]:
    """Make one long-poll request. Returns (updates, next_offset)."""
    req = urllib.request.Request(
        f"{BASE_URL}/bot{token}/getUpdates",
        data=json.dumps({"offset": offset, "timeout": POLL_TIMEOUT}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=POLL_TIMEOUT + 5) as response:
        data = json.loads(response.read())

    updates = data.get("result", [])
    next_offset = updates[-1]["update_id"] + 1 if updates else offset
    return updates, next_offset


async def async_send(token: str, chat_id: str, message: str) -> dict:
    """Async version of send — runs the blocking call in a thread."""
    import asyncio
    return await asyncio.to_thread(send, token, chat_id, message)


async def async_typing_action(token: str, chat_id: str) -> None:
    """Async version of typing_action — runs the blocking call in a thread."""
    import asyncio
    return await asyncio.to_thread(typing_action, token, chat_id)


def is_mentioned(username: str, text: str) -> bool:
    """Check if the username is mentioned in the message text."""
    return f"@{username}" in text.lower() or username.lower() in text.lower()


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_send(run, validate=None, response=None):
    """Run send against a local server, validate the request."""
    assert_call(run, validate, response or {"ok": True})


def assert_get_me(run, validate=None, response=None):
    """Run get_me against a local server, validate the request."""
    assert_call(run, validate, response or {"ok": True, "result": {}})


def assert_typing_action(run, validate=None, response=None):
    """Run typing_action against a local server."""
    assert_call(run, validate, response or {"ok": True})


def assert_call(run, validate=None, response=None):
    response_body = response or {"ok": True}
    global BASE_URL
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def _handle(self):
            content_length = self.headers.get("Content-Length")
            if content_length:
                received["body"] = json.loads(self.rfile.read(int(content_length)))
            received["path"] = self.path
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_body).encode())

        def do_POST(self): self._handle()
        def do_GET(self): self._handle()
        def log_message(self, *args): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    original = BASE_URL
    BASE_URL = f"http://127.0.0.1:{port}"

    try:
        run()
        if validate:
            validate(received)
    finally:
        BASE_URL = original
        server.shutdown()
