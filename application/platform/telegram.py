"""Telegram — Telegram Bot API communication.

Connection manages gateways keyed by bot token. Each gateway runs its
polling loop via the caller-provided polling strategy. Incoming events
are dispatched through the observer.
"""

import asyncio
import json
import os
import tempfile
import urllib.request

from application.platform.observer import (
    Command as CommandSignal, Event as EventSignal, Message as MessageSignal,
    Signal, dispatch, set_loop, subscribe, unsubscribe,
)


DEFAULT_BASE_URL = "https://api.telegram.org"
DEFAULT_TIMEOUT = 30


def get_me(token):
    """Validate a bot token via getMe. Returns the full response dict."""
    url = f"{DEFAULT_BASE_URL}/bot{token}/getMe"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())



# ── Pure helpers ─────────────────────────────────────────────────────────────

def has_command(message):
    """If the message contains a bot_command entity, return the command name."""
    for entity in message.get("entities", []):
        if entity.get("type") == "bot_command":
            offset = entity["offset"]
            length = entity["length"]
            text = message.get("text", "")
            command = text[offset:offset + length].lstrip("/").split("@")[0]
            return command
    return None


def direct_or_mentioned(username):
    """Return a filter function that passes direct messages and group mentions."""
    def filter_fn(parsed):
        if parsed["chat_type"] in ("group", "supergroup"):
            return is_mentioned(username, parsed["text"] or parsed["caption"])
        return True
    return filter_fn


def is_mentioned(username, text):
    return f"@{username}" in text.lower() or username.lower() in text.lower()


# ── Gateway ──────────────────────────────────────────────────────────────────

class Gateway:
    """A single bot token's presence on Telegram."""

    def __init__(self, token, bot_info, filter_fn=None, media_path=None):
        self.token = token
        self.bot_info = bot_info
        self.offset = 0
        self.closed = False
        self._filter_fn = filter_fn
        self._media_path = media_path


# ── Connection ───────────────────────────────────────────────────────────────

class Connection:
    """Telegram platform adapter.

    The caller provides timeout and polling strategy. Transport is
    handled internally. Signals flow through the observer.
    """

    def __init__(self, timeout, polling, base_url=DEFAULT_BASE_URL):
        self.base_url = base_url
        self.timeout = timeout
        self._polling = polling
        self._gateways = {}
        self._stopped = False

    def request(self, path, payload=None, timeout=None):
        effective_timeout = timeout if timeout is not None else self.timeout
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="POST")
        if payload is not None:
            req.data = json.dumps(payload).encode()
        kwargs = {}
        if effective_timeout is not None:
            kwargs["timeout"] = effective_timeout
        with urllib.request.urlopen(req, **kwargs) as resp:
            return json.loads(resp.read())

    def download(self, path, destination):
        urllib.request.urlretrieve(f"{self.base_url}{path}", destination)

    # ── Gateway lifecycle ────────────────────────────────────────────────

    def open_gateway(self, token, filter_by=None, media_path=None, commands=None):
        """Validate token, register gateway, start polling. Returns Gateway."""
        result = self.request(f"/bot{token}/getMe")

        if token in self._gateways:
            raise ValueError("Gateway already open for this token")
        gateway = Gateway(token, result.get("result", {}), filter_by, media_path)
        self._gateways[token] = gateway

        if commands:
            try:
                self.request(f"/bot{token}/setMyCommands", {"commands": commands})
            except Exception:
                pass

        def poll():
            while not gateway.closed and not self._stopped:
                try:
                    data = self.request(
                        f"/bot{token}/getUpdates",
                        {"offset": gateway.offset, "timeout": self.timeout},
                        timeout=self.timeout + 5,
                    )
                except Exception as e:
                    if gateway.closed or self._stopped:
                        return
                    dispatch(EventSignal("Telegram polling error", {
                        "token": token,
                        "error": str(e),
                    }))
                    return

                updates = data.get("result", [])
                if updates:
                    gateway.offset = updates[-1]["update_id"] + 1

                for update in updates:
                    if gateway.closed or self._stopped:
                        break

                    message = update.get("message", {})
                    chat_id = str(message.get("chat", {}).get("id", ""))
                    chat_type = message.get("chat", {}).get("type", "")
                    text = message.get("text", "")
                    caption = message.get("caption", "")
                    photos = message.get("photo", [])
                    msg_id = str(message.get("message_id", ""))
                    command = has_command(message)

                    parsed = {
                        "token": token,
                        "chat_id": chat_id,
                        "chat_type": chat_type,
                        "text": text,
                        "caption": caption,
                        "msg_id": msg_id,
                        "command": command,
                    }

                    if gateway._filter_fn and not gateway._filter_fn(parsed):
                        continue

                    attachment_path = None
                    if photos:
                        file_id = photos[-1].get("file_id", "")
                        if file_id:
                            try:
                                file_data = self.request(f"/bot{token}/getFile", {"file_id": file_id})
                                remote_path = file_data.get("result", {}).get("file_path", "")
                                if remote_path:
                                    ext = remote_path.rsplit(".", 1)[-1] if "." in remote_path else "jpg"
                                    media_dir = gateway._media_path
                                    if media_dir:
                                        os.makedirs(media_dir, exist_ok=True)
                                        local_path = os.path.join(media_dir, f"{file_id}.{ext}")
                                    else:
                                        fd, local_path = tempfile.mkstemp(suffix=f".{ext}")
                                        os.close(fd)
                                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                                    self.download(f"/file/bot{token}/{remote_path}", local_path)
                                    attachment_path = local_path
                            except Exception:
                                pass

                    signal_data = {
                        "token": token,
                        "chat_id": chat_id,
                        "msg_id": msg_id,
                    }

                    if command:
                        signal_data["command"] = command
                        signal_data["text"] = text
                        dispatch(CommandSignal("Telegram command received", signal_data))
                    else:
                        signal_data["content"] = text or caption
                        if attachment_path:
                            signal_data["attachment_path"] = attachment_path
                        dispatch(MessageSignal("Telegram message received", signal_data))

        self._polling(poll)

        return gateway

    def close_gateway(self, token):
        """Stop polling and remove gateway."""
        gateway = self._gateways.pop(token, None)
        if gateway:
            gateway.closed = True

    # ── Outbound ──────────────────────────────────────────────────────────

    async def send(self, token, chat_id, text):
        return await asyncio.to_thread(
            self.request, f"/bot{token}/sendMessage", {"chat_id": chat_id, "text": text})

    async def typing(self, token, chat_id):
        await asyncio.to_thread(
            self.request, f"/bot{token}/sendChatAction", {"chat_id": chat_id, "action": "typing"})

    def stop(self):
        self._stopped = True
        for token in list(self._gateways):
            self.close_gateway(token)


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_call(validate, updates=None, files=None, handle=None, polling=None):
    """Sandbox a Telegram connection against a local server.

    Starts a server that behaves like Telegram, wires the observer,
    and calls ``validate(connection, signals)``.

    ``signals(timeout)`` waits for dispatched signals (via the real
    observer) and returns them.

    Pass ``updates`` to seed getUpdates (returned once, then empty).
    Pass ``files`` mapping file_id to ``{"path": ..., "content": b...}``.
    When updates are present, polling defaults to threading.

    Returns the list of requests the server received.
    """
    import inspect
    import threading
    import time
    from http.server import HTTPServer, BaseHTTPRequestHandler

    received = []
    update_served = [False]

    if handle is None:
        def handle(path, body):
            if "/getMe" in path:
                return {"ok": True, "result": {
                    "id": 12345, "is_bot": True,
                    "first_name": "TestBot", "username": "test_bot",
                }}
            if "/getUpdates" in path:
                if updates and not update_served[0]:
                    update_served[0] = True
                    return {"ok": True, "result": updates}
                return {"ok": True, "result": []}
            if "/sendMessage" in path:
                return {"ok": True, "result": {
                    "message_id": 1,
                    "from": {"id": 12345, "is_bot": True, "first_name": "TestBot", "username": "test_bot"},
                    "chat": {"id": (body or {}).get("chat_id"), "type": "private"},
                    "date": 0,
                    "text": (body or {}).get("text", ""),
                }}
            if "/sendChatAction" in path:
                return {"ok": True, "result": True}
            if "/setMyCommands" in path:
                return {"ok": True, "result": True}
            if "/getFile" in path:
                file_id = (body or {}).get("file_id", "")
                entry = (files or {}).get(file_id, {})
                return {"ok": True, "result": {
                    "file_id": file_id,
                    "file_unique_id": file_id,
                    "file_size": len(entry.get("content", b"")),
                    "file_path": entry.get("path", f"photos/{file_id}.jpg"),
                }}
            if "/file/" in path:
                for entry in (files or {}).values():
                    if entry.get("path", "") in path:
                        return entry.get("content", b"")
                return b""
            return {"ok": True}

    if polling is None:
        polling = (lambda fn: threading.Thread(target=fn, daemon=True).start()) if updates else (lambda fn: None)

    # ── Observer setup ───────────────────────────────────────────────
    loop = asyncio.new_event_loop()
    set_loop(loop)
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()

    dispatched = []
    signal_event = threading.Event()

    async def _capture(signal: Signal):
        dispatched.append(signal)
        signal_event.set()

    subscribe(_capture)

    def signals(timeout=5):
        signal_event.wait(timeout=timeout)
        signal_event.clear()
        time.sleep(0.2)
        return list(dispatched)

    # ── Server ───────────────────────────────────────────────────────

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, path, body=None):
            received.append({"path": path, "body": body})
            result = handle(path, body)
            if isinstance(result, bytes):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                self.wfile.write(result)
            elif isinstance(result, tuple):
                s, data = result
                self.send_response(s)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else None
            self._respond(self.path, body)

        def do_GET(self):
            self._respond(self.path)

        def log_message(self, *args): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    port = server.server_address[1]

    connection = Connection(
        timeout=DEFAULT_TIMEOUT,
        polling=polling,
        base_url=f"http://127.0.0.1:{port}",
    )

    try:
        result = validate(connection, signals)
        if inspect.iscoroutine(result):
            future = asyncio.run_coroutine_threadsafe(result, loop)
            future.result(timeout=30)
    finally:
        connection.stop()
        unsubscribe(_capture)
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=5)
        loop.close()
        set_loop(None)
        server.shutdown()

    return received
