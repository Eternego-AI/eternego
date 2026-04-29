"""HTTP — make HTTP requests on behalf of the persona."""

import base64
import hashlib
import hmac
import time
import urllib.parse
import uuid

import httpx

from application.platform.tool import tool


@tool("Make an HTTP request to a URL. Use for fetching web pages, calling APIs, "
      "downloading content, or checking if a service is reachable. "
      "Returns the response body as text. For binary content, returns a summary of the response.")
async def request(method: str, url: str, body: str = "", headers: str = "") -> str:
    """Make an HTTP request and return the response text.

    method: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS.
    url: the full URL to request.
    body: request body as a string (for POST/PUT/PATCH). Empty string for no body.
    headers: headers as key:value pairs separated by newlines. Empty string for no extra headers.
    """
    parsed_headers = {}
    if headers:
        for line in headers.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                parsed_headers[key.strip()] = value.strip()

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                content=body if body else None,
                headers=parsed_headers if parsed_headers else None,
            )
            content_type = response.headers.get("content-type", "")
            if "text" in content_type or "json" in content_type or "xml" in content_type:
                return f"[{response.status_code}] {response.text[:10000]}"
            return f"[{response.status_code}] Binary response, {len(response.content)} bytes, content-type: {content_type}"
    except httpx.ConnectError as e:
        return f"[error] Could not connect: {e}"
    except httpx.TimeoutException:
        return "[error] Request timed out after 30 seconds"
    except Exception as e:
        return f"[error] {e}"


def oauth1_sign(method, url, params, consumer_secret, token_secret):
    """Compute OAuth 1.0a HMAC-SHA1 signature."""
    sorted_params = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
        for k, v in sorted(params.items())
    )
    base_string = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(sorted_params, safe=""),
    ])
    signing_key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
    digest = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


@tool("Make an OAuth 1.0a signed HTTP request. Use for APIs that require OAuth 1.0a authentication "
      "like X/Twitter. Pass the four OAuth credentials and the request details.")
async def oauth1_request(method: str, url: str, body: str = "",
                         consumer_key: str = "", consumer_secret: str = "",
                         access_token: str = "", access_token_secret: str = "") -> str:
    """Make an OAuth 1.0a signed HTTP request.

    method: GET, POST, PUT, DELETE.
    url: the full URL.
    body: request body as JSON string (for POST/PUT). Empty string for no body.
    consumer_key, consumer_secret, access_token, access_token_secret: OAuth 1.0a credentials.
    """
    parsed = urllib.parse.urlsplit(url)
    base_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    query_params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))

    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }
    oauth_params["oauth_signature"] = oauth1_sign(
        method, base_url, {**query_params, **oauth_params},
        consumer_secret, access_token_secret,
    )
    auth_header = "OAuth " + ", ".join(
        f'{k}="{urllib.parse.quote(v, safe="")}"' for k, v in sorted(oauth_params.items())
    )

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                content=body if body else None,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
            )
            content_type = response.headers.get("content-type", "")
            if "text" in content_type or "json" in content_type or "xml" in content_type:
                return f"[{response.status_code}] {response.text[:10000]}"
            return f"[{response.status_code}] Binary response, {len(response.content)} bytes, content-type: {content_type}"
    except httpx.ConnectError as e:
        return f"[error] Could not connect: {e}"
    except httpx.TimeoutException:
        return "[error] Request timed out after 30 seconds"
    except Exception as e:
        return f"[error] {e}"


# ── Assertions ───────────────────────────────────────────────────────────────

def assert_call(run, validate=None, response=None, status_code=200):
    """Run an async HTTP function against a local server, validate the request."""
    import asyncio
    import inspect
    import json
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler

    response_body = response or {"ok": True}
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def _handle(self):
            received["method"] = self.command
            received["path"] = self.path
            received["headers"] = dict(self.headers)
            content_length = self.headers.get("Content-Length")
            if content_length:
                received["body"] = self.rfile.read(int(content_length)).decode()
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_body).encode())

        def do_GET(self): self._handle()
        def do_POST(self): self._handle()
        def do_PUT(self): self._handle()
        def do_DELETE(self): self._handle()
        def log_message(self, *args): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"

    try:
        result = run(url)
        if inspect.iscoroutine(result):
            asyncio.run(result)
        if validate:
            validate(received)
    finally:
        server.shutdown()
