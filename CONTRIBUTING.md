# Eternego — Architecture



---

## Layers

The application has three layers inside `application/`:

```
business/    WHY — What should happen, reads like the README
core/        HOW — Where we as developers engineer the solutions
platform/    WHAT — What external tools actually provide, nothing more
```

Dependencies flow downward only: business imports core, core imports platform. Never upward.

The service entry point (`service.py`) and the web layer (`web/`) sit outside `application/`. They call business functions only and never touch core or platform directly. The `cli/` directory is also outside `application/` — it is the user-facing command-line interface that delegates to the service manager and business layer.

---

## Process

The order matters. We always work top-down:

1. **Write the business spec first.** Translate the README spec into a business function. The function should be self-documenting — a business person can read it and understand what happens. Add only `bus.propose` at the start, `bus.broadcast` at the end, and calls to core functions in between.

2. **Add core signatures only for what business asked for.** If the business spec calls `local_inference_engine.check(model)`, add `check(model)` to the core module. Never add core functions speculatively.

3. **Implement core functions.** This is where we engineer the solution. We figure out what steps are needed, what platform capabilities to use, and how to combine them. Core functions start with a log and use platform modules for all infrastructure.

4. **Add platform functions only for what the tool actually provides.** If Ollama has `GET /api/tags`, the platform module has `get()`. If Ollama does not have a "get default model" concept, the platform module does not have `get_default_model()` — that logic lives in core.

---

### Signals

Every business function sends at least two signals through the bus:

1. **Plan** at the start — announces intent (`bus.propose`)
2. **Event** at the end — announces result (`bus.broadcast`)

The service subscriber (`log_signal` in `service.py`) prints signals and writes them to the log file.

On failure, broadcast the failure as an event before returning. Include a `reason` key in the details.

The bus supports five signal types, each with a distinct purpose:

| Method | Signal Type | Purpose | Example |
|---|---|---|---|
| `bus.propose` | Plan | Announce intent before action | "Sensing", {"persona_id", "channel"} |
| `bus.broadcast` | Event | Announce result after action | "Sensed", {"persona_id", "channel"} |
| `bus.share` | Message | Share information passively | "Reasoning", {"content"} |
| `bus.ask` | Inquiry | Request input from subscribers | Permission check |
| `bus.order` | Command | Command an action, expect signals back | "Restart gateway", {"persona"} |

Commands (`bus.order`) are special — they expect subscribers to perform work and respond with signals. For example, the service subscribes to `"Restart gateway"` commands and stops then starts the persona's gateway.

### Error Handling

Implementation flows downward: business calls core, core calls platform. Error handling flows upward in three steps:

1. **Platform** raises raw errors (`URLError`, `subprocess.CalledProcessError`, `OSError`, keyring errors, etc.)
2. **Core** catches platform errors and raises domain exceptions (`InstallationError`, `EngineConnectionError`, `SecretStorageError`, `DiaryError`). Each core function knows what platform errors it can face.
3. **Business** catches domain exceptions and returns user-friendly `Outcome` with a broadcast event. Internal details go into the signal's details dict for logs, never into the outcome message.

Every business function wraps its logic in a try/catch for the specific domain exceptions that can happen. We already know what core functions can raise — catch those, not generic `Exception`.

Do not add try/catch to business specs before implementing core. Go down first — implement core, see what platform errors it faces, define the domain exceptions, add catches in core. Then come back up and add catches in business.

### Outcome

Every business function returns `Outcome[T]` with `success`, `message`, and optional `data`. The message is always user-friendly — no stack traces, no internal details.

---

## Core Layer

### Only what business asks for

Core functions exist because a business spec calls them. When writing a business spec, you name the core functions you need. Then you go to the core module and add their signatures. After all specs are finalized, you implement the core functions.

### Logs

Every core function starts with a log. The log title describes the action. The context dict includes relevant parameters.

```python
logger.info("Checking model availability", {"model": model})
```

### Engineering the solution

Core is where we solve problems. We decide what steps are needed and how to combine platform capabilities. If a platform tool doesn't have a concept we need, we build the logic in core using what the tool does provide.

For example, Ollama has no "get default model" concept. But it has `GET /api/tags` which lists pulled models. So core calls `ollama.get("/api/tags")` and picks the first one:

```python
async def get_default_model() -> str | None:
    """Get the default model name from the running engine."""
    logger.info("Getting default model from local inference engine")
    data = ollama.get("/api/tags")
    models = data.get("models", [])
    if not models:
        return None
    return models[0]["name"]
```

### Rules

- Core functions use platform modules for all infrastructure — never call external libraries directly.
- They do not send signals. Signals belong to the business layer.
- They do not return `Outcome`. They return domain data or raise exceptions. The business layer decides what is a success or failure.

---

## Platform Layer

### Only what the tool provides

Platform modules expose what external tools actually offer. If Ollama has an HTTP API, the platform module has `get()` and `post()`. If Linux has `which` to check installed programs, the platform module has `is_installed()`. Nothing invented, nothing wrapped beyond what the tool gives.

```python
# application/platform/ollama.py — exposes what Ollama's HTTP API provides
def get(path: str) -> dict:
    """Send a GET request to the Ollama API."""
    with urllib.request.urlopen(f"{BASE_URL}{path}") as response:
        return json.loads(response.entries())
```

### Portable

Platform modules are portable across projects. A platform module should never contain project-specific logic — that belongs in core.

This means: no project-specific defaults, no project-specific parameter names. For example, `crypto.derive_key(secret, salt)` takes a generic `secret` string and requires `salt` explicitly — the fact that we use a recovery phrase as the secret and a persona ID as the salt is a core decision, not a platform one.

### Shared modules

The `logger` and `observer` modules are shared infrastructure. The bus (`application/core/bus.py`) wraps the observer for signal dispatch. Logging is handled by the `log_signal` subscriber in `service.py`.

---