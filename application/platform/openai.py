"""OpenAI — OpenAI API communication and export parsing."""

import json
import threading
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler


BASE_URL = "https://api.openai.com"
_TIMEOUT = 120


def chat(api_key: str, model: str, messages: list[dict], json_mode: bool = False) -> str:
    """Send messages to the OpenAI API and return the response text."""
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": messages,
            "format": "json" if json_mode else "text",
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:
        data = json.loads(response.read())
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def chat_json(api_key: str, model: str, messages: list[dict]) -> dict:
    """Send messages to the OpenAI API and return the parsed JSON response."""
    response = chat(api_key, model, messages, json_mode=True)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}


def generate(api_key: str, model: str, prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to the OpenAI API and return the response text."""
    return chat(api_key, model, [{"role": "user", "content": prompt}], json_mode).strip()


def generate_json(api_key: str, model: str, prompt: str) -> dict:
    """Send a prompt to the OpenAI API and return the parsed JSON response."""
    response = generate(api_key, model, prompt, json_mode=True)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}


async def async_chat(api_key: str, model: str, messages: list[dict]) -> str:
    """Async version of chat — runs the blocking call in a thread."""
    import asyncio
    return await asyncio.to_thread(chat, api_key, model, messages)


async def async_chat_json(api_key: str, model: str, messages: list[dict]) -> dict:
    """Async version of chat_json — runs the blocking call in a thread."""
    import asyncio
    return await asyncio.to_thread(chat_json, api_key, model, messages)


def to_messages(data: str) -> list[dict]:
    """Parse OpenAI export into role-based messages."""
    export = json.loads(data)
    messages = []
    for conversation in export:
        mapping = conversation.get("mapping", {})
        for node in mapping.values():
            message = node.get("message")
            if message and message.get("content", {}).get("parts"):
                role = message["author"]["role"]
                if role not in ("user", "assistant"):
                    continue
                text = " ".join(message["content"]["parts"])
                messages.append({"role": role, "content": text})
    return messages


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_chat(run, validate=None, response=None):
    """Run chat against a local server, validate the request, return controlled response."""
    assert_call(run, validate, response or {"choices": [{"message": {"content": ""}}]})


def assert_chat_json(run, validate=None, response=None):
    """Run chat_json against a local server, validate the request, return controlled response."""
    assert_call(run, validate, response or {"choices": [{"message": {"content": "{}"}}]})


def assert_call(run, validate, response_body):
    global BASE_URL
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received["body"] = body
            received["headers"] = dict(self.headers)
            received["path"] = self.path
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_body).encode())
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
