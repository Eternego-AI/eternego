"""Discord — Discord Bot API communication (REST + gateway).

Connection manages gateways keyed by bot token. Each gateway runs a
WebSocket session on a background thread. Incoming events are
dispatched through the observer.
"""

import asyncio
import json
import urllib.request

from application.platform.observer import (
    Event as EventSignal, Message as MessageSignal,
    Signal, dispatch, set_loop, subscribe, unsubscribe,
)


DEFAULT_BASE_URL = "https://discord.com/api/v10"
DEFAULT_GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"


def get_me(token):
    """Validate a bot token via /users/@me. Returns the user dict."""
    url = f"{DEFAULT_BASE_URL}/users/@me"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bot {token}",
        "User-Agent": "DiscordBot (eternego, 0.1)",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

INTENT_GUILDS = 1 << 0
INTENT_GUILD_MESSAGES = 1 << 9
INTENT_DIRECT_MESSAGES = 1 << 12
INTENT_MESSAGE_CONTENT = 1 << 15

OP_DISPATCH = 0
OP_HEARTBEAT = 1
OP_IDENTIFY = 2
OP_RESUME = 6
OP_RECONNECT = 7
OP_INVALID_SESSION = 9
OP_HELLO = 10
OP_HEARTBEAT_ACK = 11


# ── Gateway ──────────────────────────────────────────────────────────────────

class Gateway:
    """A single bot token's presence on Discord."""

    def __init__(self, token, bot_info, intents, filter_fn=None):
        self.token = token
        self.bot_info = bot_info
        self.intents = intents
        self.closed = False
        self._filter_fn = filter_fn
        self._session_id = None
        self._resume_url = None
        self._last_seq = None


# ── Connection ───────────────────────────────────────────────────────────────

class Connection:
    """Discord platform adapter.

    The caller provides timeout. The WebSocket gateway runs on a
    background thread internally. Signals flow through the observer.
    """

    def __init__(self, timeout, websocket, properties, user_agent,
                 base_url=DEFAULT_BASE_URL, gateway_url=DEFAULT_GATEWAY_URL):
        self.base_url = base_url
        self.gateway_url = gateway_url
        self.timeout = timeout
        self.user_agent = user_agent
        self.properties = properties
        self._websocket = websocket
        self._gateways = {}
        self._stopped = False

    def request(self, method, path, token, payload=None):
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bot {token}",
            "User-Agent": self.user_agent,
        }
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read()
            if not raw:
                return {}
            return json.loads(raw)

    # ── Gateway lifecycle ────────────────────────────────────────────────

    def open_gateway(self, token, intents=INTENT_DIRECT_MESSAGES, filter_by=None):
        """Validate token, register gateway, start WebSocket session."""
        import websockets

        result = self.request("GET", "/users/@me", token)

        if token in self._gateways:
            raise ValueError("Gateway already open for this token")
        gateway = Gateway(token, result, intents, filter_by)
        self._gateways[token] = gateway

        async def session():
            while not gateway.closed and not self._stopped:
                heartbeat_task = None
                try:
                    url = gateway._resume_url or self.gateway_url
                    async with websockets.connect(url) as ws:
                        hello = json.loads(await ws.recv())
                        interval = hello.get("d", {}).get("heartbeat_interval", 45000) / 1000

                        async def heartbeat():
                            try:
                                while not gateway.closed:
                                    await asyncio.sleep(interval)
                                    await ws.send(json.dumps({"op": OP_HEARTBEAT, "d": gateway._last_seq}))
                            except (asyncio.CancelledError, Exception):
                                return

                        heartbeat_task = asyncio.create_task(heartbeat())

                        if gateway._session_id and gateway._resume_url:
                            await ws.send(json.dumps({
                                "op": OP_RESUME,
                                "d": {
                                    "token": token,
                                    "session_id": gateway._session_id,
                                    "seq": gateway._last_seq,
                                },
                            }))
                        else:
                            await ws.send(json.dumps({
                                "op": OP_IDENTIFY,
                                "d": {
                                    "token": token,
                                    "intents": gateway.intents,
                                    "properties": self.properties,
                                },
                            }))

                        async for raw in ws:
                            if gateway.closed or self._stopped:
                                return

                            event = json.loads(raw)
                            op = event.get("op")

                            if op == OP_RECONNECT:
                                break
                            if op == OP_INVALID_SESSION:
                                gateway._session_id = None
                                gateway._resume_url = None
                                gateway._last_seq = None
                                await asyncio.sleep(1)
                                break
                            if op != OP_DISPATCH:
                                continue

                            seq = event.get("s")
                            if seq is not None:
                                gateway._last_seq = seq

                            event_type = event.get("t")
                            data = event.get("d") or {}

                            if event_type == "READY":
                                gateway._session_id = data.get("session_id")
                                gateway._resume_url = data.get("resume_gateway_url")
                                continue

                            if event_type != "MESSAGE_CREATE":
                                continue

                            author = data.get("author") or {}
                            if author.get("bot"):
                                continue

                            channel_id = str(data.get("channel_id", ""))
                            content = data.get("content", "") or ""
                            attachments = data.get("attachments") or []
                            msg_id = str(data.get("id", ""))

                            parsed = {
                                "token": token,
                                "channel_id": channel_id,
                                "content": content,
                                "author_id": str(author.get("id", "")),
                                "msg_id": msg_id,
                            }

                            if gateway._filter_fn and not gateway._filter_fn(parsed):
                                continue

                            signal_data = dict(parsed)

                            if attachments:
                                att = attachments[0]
                                signal_data["attachment_url"] = att.get("url", "")
                                signal_data["attachment_filename"] = att.get("filename", "")
                                signal_data["attachment_content_type"] = att.get("content_type", "")

                            dispatch(MessageSignal("Discord message received", signal_data))

                except asyncio.CancelledError:
                    return
                except Exception as e:
                    if gateway.closed or self._stopped:
                        return
                    dispatch(EventSignal("Discord gateway error", {
                        "token": token,
                        "error": str(e),
                    }))
                    return
                finally:
                    if heartbeat_task:
                        heartbeat_task.cancel()
                        try:
                            await heartbeat_task
                        except (asyncio.CancelledError, Exception):
                            pass

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(session())
            finally:
                loop.close()

        self._websocket(run)

        return gateway

    def close_gateway(self, token):
        """Stop gateway and remove it."""
        gateway = self._gateways.pop(token, None)
        if gateway:
            gateway.closed = True

    # ── Outbound ──────────────────────────────────────────────────────────

    async def send(self, token, channel_id, text):
        return await asyncio.to_thread(
            self.request, "POST", f"/channels/{channel_id}/messages", token, {"content": text})

    async def typing(self, token, channel_id):
        await asyncio.to_thread(
            self.request, "POST", f"/channels/{channel_id}/typing", token)

    def stop(self):
        self._stopped = True
        for token in list(self._gateways):
            self.close_gateway(token)


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_call(validate, events=None, handle=None, websocket=None):
    """Sandbox a Discord connection against local servers.

    Starts an HTTP server (REST) and optionally a WebSocket server
    (gateway). Creates a Connection and calls ``validate(connection, signals)``.

    Pass ``events`` as a list of gateway event dicts with ``t`` and ``d``
    keys to seed the WebSocket server.

    Returns the list of REST requests the server received.
    """
    import inspect
    import threading
    import time
    from http.server import HTTPServer, BaseHTTPRequestHandler

    received = []

    if handle is None:
        def handle(method, path, body, headers):
            if "/users/@me" in path:
                return {"id": "12345", "username": "test_bot", "bot": True,
                        "discriminator": "0000", "avatar": None}
            if "/messages" in path and method == "POST":
                return {"id": "msg-1", "channel_id": path.split("/")[2],
                        "content": (body or {}).get("content", ""),
                        "author": {"id": "12345", "username": "test_bot", "bot": True}}
            if "/typing" in path:
                return (204, None)
            return {"ok": True}

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

    # ── HTTP server (REST) ───────────────────────────────────────────

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, method):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else None
            headers = {
                "Authorization": self.headers.get("Authorization", ""),
                "User-Agent": self.headers.get("User-Agent", ""),
            }
            received.append({"method": method, "path": self.path, "body": body, "headers": headers})

            result = handle(method, self.path, body, headers)
            if isinstance(result, tuple):
                status, data = result
                self.send_response(status)
                if data is not None:
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode())
                else:
                    self.end_headers()
            elif isinstance(result, dict):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self.send_response(204)
                self.end_headers()

        def do_GET(self): self._respond("GET")
        def do_POST(self): self._respond("POST")
        def do_PUT(self): self._respond("PUT")
        def do_DELETE(self): self._respond("DELETE")
        def log_message(self, *args): pass

    http_server = HTTPServer(("127.0.0.1", 0), Handler)
    http_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    http_thread.start()
    http_port = http_server.server_address[1]

    # ── WebSocket server (gateway) ───────────────────────────────────
    ws_server = None
    ws_port = None

    if events is not None:
        import websockets

        async def ws_handler(websocket):
            await websocket.send(json.dumps({
                "op": OP_HELLO, "d": {"heartbeat_interval": 45000},
            }))

            while True:
                msg = json.loads(await websocket.recv())
                if msg["op"] == OP_HEARTBEAT:
                    await websocket.send(json.dumps({"op": OP_HEARTBEAT_ACK}))
                    continue
                if msg["op"] == OP_IDENTIFY:
                    break

            await websocket.send(json.dumps({
                "op": OP_DISPATCH, "t": "READY", "s": 1,
                "d": {"session_id": "test-session", "resume_gateway_url": None},
            }))

            for i, event in enumerate(events, start=2):
                await websocket.send(json.dumps({
                    "op": OP_DISPATCH, "t": event["t"], "s": i, "d": event["d"],
                }))

            try:
                async for raw in websocket:
                    msg = json.loads(raw)
                    if msg["op"] == OP_HEARTBEAT:
                        await websocket.send(json.dumps({"op": OP_HEARTBEAT_ACK}))
            except websockets.ConnectionClosed:
                pass

        async def start_ws():
            return await websockets.serve(ws_handler, "127.0.0.1", 0)

        future = asyncio.run_coroutine_threadsafe(start_ws(), loop)
        ws_server = future.result(timeout=5)
        ws_port = ws_server.sockets[0].getsockname()[1]

    connection = Connection(
        timeout=30,
        websocket=websocket or (lambda fn: threading.Thread(target=fn, daemon=True).start()),
        properties={"os": "test", "browser": "test", "device": "test"},
        user_agent="DiscordBot (test, 0.1)",
        base_url=f"http://127.0.0.1:{http_port}",
        gateway_url=f"ws://127.0.0.1:{ws_port}" if ws_port else DEFAULT_GATEWAY_URL,
    )

    try:
        result = validate(connection, signals)
        if inspect.iscoroutine(result):
            future = asyncio.run_coroutine_threadsafe(result, loop)
            future.result(timeout=30)
    finally:
        connection.stop()
        if ws_server:
            ws_server.close()
            asyncio.run_coroutine_threadsafe(ws_server.wait_closed(), loop).result(timeout=5)
        unsubscribe(_capture)
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=5)
        loop.close()
        set_loop(None)
        http_server.shutdown()

    return received
