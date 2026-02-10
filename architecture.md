# Eternego — Architecture

This document defines how to translate the project's documentation into code and the process to follow when building each layer.

---

## Layers

The application has three layers inside `application/`:

```
business/    WHY — What should happen, reads like the README
core/        HOW — Where we as developers engineer the solutions
platform/    WHAT — What external tools actually provide, nothing more
```

Dependencies flow downward only: business imports core, core imports platform. Never upward.

The presentation layer (`telegram/` for MVP) sits outside `application/`. It calls business functions and subscribes to signals. It never touches core or platform directly.

---

## Process

The order matters. We always work top-down:

1. **Write the business spec first.** Translate the README spec into a business function. The function should be self-documenting — a business person can read it and understand what happens. Add only `bus.propose` at the start, `bus.broadcast` at the end, and calls to core functions in between.

2. **Add core signatures only for what business asked for.** If the business spec calls `local_inference_engine.check(model)`, add `check(model)` to the core module. Never add core functions speculatively.

3. **Implement core functions.** This is where we engineer the solution. We figure out what steps are needed, what platform capabilities to use, and how to combine them. Core functions start with a log and use platform modules for all infrastructure.

4. **Add platform functions only for what the tool actually provides.** If Ollama has `GET /api/tags`, the platform module has `get()`. If Ollama does not have a "get default model" concept, the platform module does not have `get_default_model()` — that logic lives in core.

---

## Business Layer

### Translating from README

Each business specification in README.md becomes a function in a business module. The spec description becomes the function's docstring. The numbered steps become the function body.

There are three business modules:

| Module | Scope |
|---|---|
| `environment.py` | Preparing and verifying the environment |
| `persona.py` | Persona lifecycle: creation, migration, identity, learning, diary, sleep |
| `gateway.py` | Managing communication channels: add, verify, update |

### Signals

Every business function sends at least two signals through the bus:

1. **Plan** at the start — announces intent (`bus.propose`)
2. **Event** at the end — announces result (`bus.broadcast`)

The bus logs automatically on every call, so signals double as the business layer's log trail.

On failure, broadcast the failure as an event before returning. Include a `reason` key in the details.

### Error Handling

Implementation flows downward: business calls core, core calls platform. Error handling flows upward: platform raises raw errors, core may raise domain exceptions (e.g. `UnsupportedOS`), business catches them all and turns them into user-friendly outcomes with broadcast events.

Every business function wraps its logic in a try/catch for the specific exceptions that can happen. We already know what core functions can raise — catch those, not generic `Exception`. On each caught exception, broadcast a failure event with the error details and return a failed `Outcome` with a user-friendly message. Internal details go into the signal's details dict for logs, never into the outcome message.

### Outcome

Every business function returns `Outcome[T]` with `success`, `message`, and optional `data`. The message is always user-friendly — no stack traces, no internal details.

### Example — from the actual codebase

README Spec 1 says:

> It makes it easy to set up and prepare an environment for your persona to grow.
>
> 1. Check if a local inference engine is installed, if not install it
> 2. Pull at least one model and verify it is available and running

Translated to `application/business/environment.py`:

```python
async def prepare(model: str | None = None) -> Outcome[dict]:
    """It makes it easy to set up and prepare an environment for your persona to grow."""
    await bus.propose("Preparing environment", {"model": model})

    try:
        if not await local_inference_engine.is_installed():
            await local_inference_engine.install()

        if not model:
            model = await local_inference_engine.get_default_model()

        if not model:
            await bus.broadcast("Environment preparation failed", {"reason": "no_model"})
            return Outcome(success=False, message="No model available. Please provide a model name.")

        if not await local_inference_engine.check(model):
            await local_inference_engine.pull(model)

        outcome = await check_model(model)
        if not outcome.success:
            await bus.broadcast("Environment preparation failed", {"model": model})
            return Outcome(success=False, message="Environment preparation failed")

        await bus.broadcast("Environment ready", {"model": model})

        return Outcome(success=True, message="Environment is ready", data={"model": model})

    except UnsupportedOS as e:
        await bus.broadcast("Environment preparation failed", {
            "reason": "unsupported_os",
            "error": str(e),
        })
        return Outcome(success=False, message="Your operating system is not supported. Eternego requires Linux, macOS, or Windows.")

    except URLError as e:
        await bus.broadcast("Environment preparation failed", {
            "reason": "connection",
            "model": model,
            "error": str(e),
        })
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")
```

Notice: the business spec called `is_installed`, `install`, `get_default_model`, `check`, and `pull`. Those are the only functions that exist in the core module — because the spec asked for them.

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

### Single ownership of paths and constants

If a path or constant belongs to a module, other modules receive it as a parameter — they don't compute it themselves. For example, the persona directory path lives only in `identity.memory_path(persona)`. The diary module receives the path, it never imports `PERSONAS_DIR`.

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
        return json.loads(response.read())
```

### Portable

Platform modules are portable across projects. We copied `logger` and `observer` directly from another project. A platform module should never contain project-specific logic — that belongs in core.

This means: no project-specific defaults, no project-specific parameter names. For example, `crypto.derive_key(secret, salt)` takes a generic `secret` string and requires `salt` explicitly — the fact that we use a recovery phrase as the secret and a persona ID as the salt is a core decision, not a platform one.

### Shared modules

The `logger` and `observer` modules are shared infrastructure. The bus (`application/core/bus.py`) wraps the observer and adds automatic logging on every signal.

---

## How It Connects

```
README spec                    -->  business function (bus.propose, core calls, bus.broadcast)
  business calls core function -->  we add the signature, then engineer the solution
    core uses platform         -->  only what the tool actually provides
```

The README tells you WHAT to build in business. We as developers figure out HOW in core. Platform gives us the raw tools to work with.
