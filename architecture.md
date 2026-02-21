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

The service entry point (`service.py`) and the web layer (`web/`) sit outside `application/`. They call business functions only and never touch core or platform directly. The `cli/` directory is also outside `application/` — it is the user-facing command-line interface that delegates to the service manager and business layer.

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

There are two business modules:

| Module | Scope |
|---|---|
| `environment.py` | Preparing and verifying the environment |
| `persona.py` | Persona lifecycle: creation, migration, identity, learning, interaction, diary, gateway start/stop |

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

### Example — from the actual codebase

README Spec 1 says:

> It makes it easy to set up and prepare an environment for your persona to grow.
>
> 1. Check if required tools are installed, if not install them
> 2. Check if a local inference engine is installed, if not install it
> 3. Pull at least one model and verify it is available and running

Translated to `application/business/environment.py`:

```python
async def prepare(model: str | None = None) -> Outcome[dict]:
    """It makes it easy to set up and prepare an environment for your persona to grow."""
    await bus.propose("Preparing environment", {"model": model})

    try:
        if not await system.is_installed("git"):
            await system.install("git")

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
        await bus.broadcast("Environment preparation failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except InstallationError as e:
        await bus.broadcast("Environment preparation failed", {"reason": "installation", "error": str(e)})
        return Outcome(success=False, message=str(e))

    except EngineConnectionError as e:
        await bus.broadcast("Environment preparation failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine.")
```

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

If a path or constant belongs to a module, other modules receive it as a parameter — they don't compute it themselves. For example, the persona directory path lives only in `Persona.storage_dir`. The diary module receives the path, it never imports the base directory.

### When to merge vs. separate core modules

If two core modules manage the same concept or data, merge them. If a module manages a distinct concern, keep it separate. For example, `diary` is separate from `agent` because backup/versioning is a different concern from persona identity management.

### Persona is config, files are state

The `Persona` dataclass holds configuration and metadata: id, name, model, frontier, channels. The files on disk (identity buckets, instructions, skills, training data) are the persona's state, managed by `agent` and `person`. When someone asks who I am, I give my name — not my skills or assets.

### Rules

- Core functions use platform modules for all infrastructure — never call external libraries directly.
- They do not send signals. Signals belong to the business layer.
- They do not return `Outcome`. They return domain data or raise exceptions. The business layer decides what is a success or failure.

---

## The Cognitive Architecture

The interaction system uses a cognitive model that mirrors human cognition. This is the central design pattern for how the persona processes and responds to the world.

### Brain and Abilities

The brain (`core/brain.py`) is the persona's reasoning loop. It calls the local model, parses its JSON response, and dispatches to ability functions based on the keys in the response. The brain runs as a background task — it never blocks the caller.

```
hear (business) → brain.reason (core, background)
  → local_model.respond → parse JSON → dispatch abilities
    → say   → gateway.send
    → act   → system.execute
    → escalate → frontier.respond
    → remember_fact, load_trait, ... → disk
  → repeat until model returns {}
  → history.persist
```

Abilities live in `core/abilities.py`. Each is a plain `async` function decorated with `@ability(description, order)`. The brain discovers them by reflection. An ability receives `(persona, thread, items)` and returns either a `Prompt` to feed back into the next reasoning cycle, or `None` to continue silently.

### The Abilities Contract

**Exception handling belongs in the brain, not in abilities.**

The brain wraps every ability call in `try/except`:

```python
try:
    result = await fn(persona, thread, value)
    if result:
        new_prompts.append(result)
except Exception as e:
    new_prompts.append(Prompt(role="user", content=f"{key} failed: {e}"))
```

This is the permanent, guaranteed connection between the brain and every ability. If an ability raises, the brain converts it to a `Prompt` and the persona can reason about what went wrong and adapt — retry, try a different approach, or inform the person.

If abilities had their own top-level `try/except`, they could swallow exceptions and return `None`, silently breaking the connection. The brain would never know something failed, and the persona would carry on as if nothing happened.

**Abilities may do internal self-correction** — retrying a flaky call, trying an alternative, falling back to a simpler approach. When they do, they should honour the contract:

- Return a `Prompt` with meaningful feedback if the brain should know what happened.
- Return `None` if the situation was fully resolved and no further reasoning is needed.
- Let exceptions propagate for genuine failures — the brain will handle them.

### The Reasoning Loop

The brain's `_reason()` function runs a `while True` loop:

1. Call `local_model.respond()` with the current message history.
2. Parse the JSON response — each key is an ability name, value is a list of items.
3. Dispatch to each named ability, collect returned `Prompt` objects.
4. If no prompts were returned, break — reasoning is done.
5. Otherwise, append the prompts to messages and loop.

This lets the persona chain naturally — think, act, see the result, think again — without the business layer needing to re-invoke anything.

### Memory vs History

**Memory** is short-term, in-process, per persona. The `memories` module (`application/core/memories.py`) holds documents for the current session:

- `memories.agent(persona).remember(document)` — append a document to the current thread
- `memories.agent(persona).as_messages(thread_id)` — return memory as LLM chat messages
- `memories.agent(persona).as_transcript()` — return memory as a numbered transcript
- `memories.agent(persona).filter_by(predicate)` — query memory with a closure
- `memories.agent(persona).forget_everything()` — clear all memory for this persona

**History** is long-term, on disk. The `history/` directory stores conversation files that persist across sessions. Used for oversight (`history.entries()`), control (`history.delete()`), and consolidation at sleep time (`history.consolidate()`).

### Networks, Connections, and Gateways

Three distinct concepts — do not conflate them:

| Concept | Scope | Lives in |
|---|---|---|
| **Network** | Config — a named external service (telegram token) | `Persona.networks`, `config.json` |
| **Connection** | Runtime persistent — one polling thread per network, started on app start | `core/connections.py`, `_pollers` dict |
| **Gateway** | Runtime ephemeral — one per conversation (one per `chat_id` for telegram, one per request for web) | `core/gateways.py`, `_active` dict |

A `Connection` starts when `persona.start()` is called. For telegram it starts a polling thread. As each verified `chat_id` sends a message, the connection creates a `Gateway` for that chat and registers it. The `Gateway` holds closures for `send`, `stop`, `wait`, and `verify` — it knows how to reach a specific person without exposing credentials to the rest of the system.

Unverified senders are gated before a Gateway is ever created — see **Channel Pairing** below.

### Channel Pairing

Verified channels are stored in `channels.md` (gitignored) per persona. On each incoming message, `connections.bridge` calls `channels.is_verified`. If the `chat_id` is not verified:

1. `pairing.generate(persona_id, network_id, chat_id)` creates a 6-char alphanumeric code (36^6 ≈ 2.1B combinations) stored in memory with a 10-minute expiry.
2. The code is sent back to the unknown sender via Telegram.
3. The person runs `eternego pair <code>` on their local machine.
4. The CLI calls `environment.pair(code)` → `pairing.claim` → `channels.add` → persists to `channels.md`.
5. The next message from that `chat_id` passes the verification check and proceeds normally.

`channels.md` is gitignored so migrating to a new environment requires re-pairing — each environment is a fresh trust boundary.

For web requests, the route creates a `Channel` and calls `persona.connect()` to get a `Gateway` backed by an `asyncio.Future`. The route calls `persona.hear()` to start reasoning, then `await gw.wait()` to block until the persona responds. `persona.disconnect()` closes the gateway when done.

### Escalation

The escalation flow connects the local model to a more powerful frontier model:

1. The persona uses the `escalate` ability with a question.
2. `frontier.respond()` sends the question to the configured frontier model and returns the answer.
3. The answer is returned as a `Prompt` — the persona reasons about it and continues.

The persona does not observe the frontier's reasoning, only its answer. Like asking an expert a question — you get the conclusion, not their internal deliberation.

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

### Normalized output for frontier models

The `anthropic` and `openai` platform modules both stream and normalize their output to the same shape:

```python
{"message": {"content": "...", "tool_calls": [...]}, "done": bool}
```

This lets the frontier module (`application/core/frontier.py`) process both providers identically. The platform handles the protocol differences (SSE parsing, different event structures); core sees a uniform stream.

### Portable

Platform modules are portable across projects. A platform module should never contain project-specific logic — that belongs in core.

This means: no project-specific defaults, no project-specific parameter names. For example, `crypto.derive_key(secret, salt)` takes a generic `secret` string and requires `salt` explicitly — the fact that we use a recovery phrase as the secret and a persona ID as the salt is a core decision, not a platform one.

### Shared modules

The `logger` and `observer` modules are shared infrastructure. The bus (`application/core/bus.py`) wraps the observer for signal dispatch. Logging is handled by the `log_signal` subscriber in `service.py`.

---

## Data Models

All shared data types live in `application/core/data.py`:

| Class | Purpose |
|---|---|
| `Network` | Config for an external service — type ("telegram") + credentials. Stored in `Persona.networks`. |
| `Channel` | A conversation address — type + name (chat_id for telegram, uuid for web). No credentials. |
| `Message` | An incoming message — channel it arrived on + text content. |
| `Model` | AI model reference (name, provider, credentials) |
| `Observation` | Extracted observations from conversations (facts, traits, context, struggles — all required, no defaults) |
| `Gateway` | A live conversation channel — closure-based send/stop/wait/verify for a specific Channel. |
| `Persona` | Persona configuration (id, name, model, base_model, frontier, networks, storage_dir) |

Short-term memory is per-persona and lives in the `memories` module, not in `data.py`.

---

## Domain Exceptions

All domain exceptions live in `application/core/exceptions.py`:

| Exception | Raised By | Meaning |
|---|---|---|
| `UnsupportedOS` | system, local_inference_engine | OS is not Linux, macOS, or Windows |
| `InstallationError` | system | Failed to install a program |
| `EngineConnectionError` | local_model, local_inference_engine | Cannot reach Ollama |
| `SecretStorageError` | system | Cannot access OS secure storage |
| `DiaryError` | diary | Failed to read/write diary |
| `IdentityError` | agent | Failed to read/write persona files |
| `PersonError` | person | Failed to read/write person files |
| `ExternalDataError` | external_llms | Failed to parse external AI export |
| `FrontierError` | frontier | Failed to reach or parse frontier API |
| `ExecutionError` | system | Failed to execute a tool call |
| `NetworkError` | connections | Failed to connect to or send on a network |
| `NetworkVerificationRequired` | connections | Unverified chat_id attempted to message (legacy, replaced by pairing flow) |
| `PairingError` | pairing, channels | Pairing code invalid, expired, or channel save failed |

---

## How It Connects

```
README spec                    -->  business function (bus.propose, core calls, bus.broadcast)
  business calls core function -->  we add the signature, then engineer the solution
    core uses platform         -->  only what the tool actually provides
```

The README tells you WHAT to build in business. We as developers figure out HOW in core. Platform gives us the raw tools to work with.

For interaction specs, the cognitive architecture adds another dimension:

```
persona.hear (business) → brain.reason (core, background)
  → local_model.respond → parse JSON
    → say       → gateway.send → telegram/web
    → act       → system.execute
    → escalate  → frontier.respond → anthropic/openai
    → learn_identity, remember_trait, feel_struggle, update_context → disk (async)
    → check/ask/resolve_permission → permissions.md (with fallback prompts)
  → loop until model returns {}
  → history.persist

service.py → persona.start (business) → connections.connect (core) → telegram.poll (platform, in thread)
             incoming message → channels.is_verified?
               no  → pairing.generate → telegram.send (code to sender)
               yes → Gateway created → persona.hear → brain.reason
           → persona.stop (business) → connections.disconnect_all (core)
           → sleep_loop (nightly) → persona.sleep (business)
           → start_web (uvicorn) → web/routes → persona.* / environment.* (business)

web/routes/openai.py → persona.connect → gateway with asyncio.Future
                     → persona.hear → brain.reason (background)
                     → gw.wait() → response
                     → persona.disconnect
web/routes/api.py    → environment.pair / persona.create / migrate / control (business)

cli/ → environment.pair(code) → pairing.claim → channels.add
     → environment.prepare / check_model
```
