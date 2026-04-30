"""Smoke test for a running Eternego daemon.

Run after `eternego daemon` (or any installed wrapper) is up and Ollama has
the model pulled. Verifies the create-persona path end-to-end: provider
probe, local model check, channel validation (when tokens given), persona
spawn, manager.add. Anything past the API contract — model output quality,
cognitive cycle behavior — is out of scope.

Environment:
    ETERNEGO_URL       Base URL of the daemon (default http://localhost:5000)
    OLLAMA_URL         Ollama endpoint (default http://localhost:11434)
    OLLAMA_MODEL       Model name to use (default qwen2.5:0.5b)
    TELEGRAM_TOKEN     Optional — if set, validates as a real Telegram bot
    DISCORD_TOKEN      Optional — if set, validates as a real Discord bot

Exits 0 on success, non-zero with a printed reason on failure.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request


ETERNEGO_URL = os.environ.get("ETERNEGO_URL", "http://localhost:5000").rstrip("/")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or None
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN") or None


def request(method: str, path: str, payload: dict | None = None, timeout: float = 300.0) -> tuple[int, dict | str]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(f"{ETERNEGO_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def wait_for_daemon(retries: int = 120, delay: float = 1.0) -> None:
    """Poll /api/personas until the daemon answers. ~2 min budget — daemon
    boot + lazy provider import on first request can run slow on cold runners."""
    last = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(f"{ETERNEGO_URL}/api/personas", timeout=5) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last = e
        time.sleep(delay)
    raise RuntimeError(f"Daemon never became reachable at {ETERNEGO_URL} ({last})")


def main() -> int:
    print(f"[*] waiting for daemon at {ETERNEGO_URL}")
    wait_for_daemon()
    print("[*] daemon reachable")

    payload: dict = {
        "name": "smoke-test",
        "thinking_url": OLLAMA_URL,
        "thinking_model": OLLAMA_MODEL,
    }
    if TELEGRAM_TOKEN:
        payload["telegram_token"] = TELEGRAM_TOKEN
        print("[*] including telegram_token (validates against api.telegram.org)")
    if DISCORD_TOKEN:
        payload["discord_token"] = DISCORD_TOKEN
        print("[*] including discord_token (validates against discord.com)")

    print(f"[*] POST /api/persona/create with model={OLLAMA_MODEL}")
    status, body = request("POST", "/api/persona/create", payload)

    if status != 200:
        print(f"[FAIL] persona/create returned {status}: {body}", file=sys.stderr)
        return 1

    persona = body.get("persona") if isinstance(body, dict) else None
    if not persona or not persona.get("id"):
        print(f"[FAIL] persona/create succeeded but response shape was unexpected: {body}", file=sys.stderr)
        return 1

    persona_id = persona["id"]
    print(f"[OK] persona created — id={persona_id} name={persona.get('name')}")

    print(f"[*] POST /api/persona/{persona_id}/delete")
    status, body = request("POST", f"/api/persona/{persona_id}/delete")
    if status != 200:
        print(f"[WARN] delete returned {status}: {body} (persona file remains in ETERNEGO_HOME)")
    else:
        print("[OK] persona deleted")

    return 0


if __name__ == "__main__":
    sys.exit(main())
