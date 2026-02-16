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
| `persona.py` | Persona lifecycle: creation, migration, identity, learning, interaction, diary |
| `gateway.py` | Managing communication channels: add, verify, update |

### Signals

Every business function sends at least two signals through the bus:

1. **Plan** at the start — announces intent (`bus.propose`)
2. **Event** at the end — announces result (`bus.broadcast`)

The bus logs automatically on every call, so signals double as the business layer's log trail.

On failure, broadcast the failure as an event before returning. Include a `reason` key in the details.

The bus supports five signal types, each with a distinct purpose:

| Method | Signal Type | Purpose | Example |
|---|---|---|---|
| `bus.propose` | Plan | Announce intent before action | "Sensing", {"persona_id", "channel"} |
| `bus.broadcast` | Event | Announce result after action | "Sensed", {"persona_id", "channel"} |
| `bus.share` | Message | Share information passively | "Reasoning", {"content"} |
| `bus.ask` | Inquiry | Request input from subscribers | Permission check |
| `bus.order` | Command | Command an action, expect signals back | "Say", {"content", "channels"} |

Commands (`bus.order`) are special — they expect subscribers to perform work and respond with signals. For example, the `say` spec orders channels to communicate, and channels respond with `"Communicated"` signals that the spec checks.

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

### Thought and Thinking

Every reasoning process — whether from the local model or a frontier model — yields `Thought` objects. Each thought has an `intent` that tells the business layer what to do with it:

```python
@dataclass(kw_only=True)
class Thought:
    intent: str       # "saying", "doing", "consulting", "reasoning"
    content: str = ""
    tool_calls: list[dict] | None = None

class Thinking:
    """The thinking process — wraps a reasoning function to yield thoughts."""
    def __init__(self, reason_by: Callable[[], AsyncIterator[Thought]]):
        self._reason = reason_by

    def reason(self) -> AsyncIterator[Thought]:
        return self._reason()
```

`Thinking` is reusable. It wraps any async generator that yields thoughts. The business layer doesn't care whether the thoughts come from a local model or a frontier API — it routes them the same way.

### The fluent API

The agent exposes a fluent interface for triggering thought:

```python
think = agent.given(persona, {"type": "stimulus", "role": "user", "content": prompt})
async for thought in think.reason():
    if thought.intent == "saying":
        await say(persona, thought, channel)
    elif thought.intent == "doing":
        await act(persona, thought)
    elif thought.intent == "consulting":
        await escalate(persona, thought.content, channel)
```

`agent.given()` stores the input in memory and returns a `Thinking` object. Calling `.reason()` starts the async generator. The same pattern works for frontier:

```python
async for thought in frontier.consulting(persona, prompt).reason():
    ...
```

### Intent detection

The local model streams tokens. The agent detects intents through XML-like tags embedded in the stream:

- `<think>...</think>` → `intent="reasoning"` (internal, not shown to person)
- `<escalate>...</escalate>` → `intent="consulting"` (content sent to frontier)
- Tool calls in response → `intent="doing"`
- Plain text → `intent="saying"`

The frontier uses the same `<think>` detection but cannot escalate (no infinite escalation).

### The action loop

When the agent yields a "doing" thought, the business layer executes the tool and notes the result via `memories.agent(persona).remember()`. The reasoning loop inside `agent.reason()` uses a `while True` that only breaks when the agent produces no actions in a cycle. This means the agent can chain multiple tool calls naturally — think, act, see result, think again — without recursive calls.

### Memory vs History

**Memory** is short-term, in-process, per persona. The `memories` module (`application/core/memories.py`) holds documents for the current session:

- `memories.agent(persona)` — returns a handle for that persona's memory
- `memories.agent(persona).remember(document)` — append a document (creates memory if needed)
- `memories.agent(persona).recall()` — return all documents (a copy)
- `memories.agent(persona).forget_everything()` — clear that persona's memory

The agent writes to memory via `memories.agent(persona).remember()`: `agent.given()` appends the stimulus; the business layer appends act results, delivery confirmations, and frontier observations. When building messages for the model, the agent iterates `memories.agent(persona).recall()` and maps each document type to the appropriate message role (user, assistant, tool).

**History** is long-term, on disk. The `history/` directory stores conversation files that persist across sessions. Used for oversight (listing), control (deletion), and sleep (observation extraction via `agent.recall()`).

### Escalation

The escalation flow connects the local model to a more powerful frontier model:

1. The local model detects it can't handle something → wraps reason in `<escalate>` tags.
2. The agent yields `Thought(intent="consulting")`.
3. The business layer calls `escalate`, which uses `frontier.consulting()`.
4. The frontier streams through the same `Thinking` pattern.
5. Frontier thoughts are routed through `say` and `act`.
6. After completion, the full interaction (minus reasoning) is stored via `memories.agent(persona).remember({"type": "observation", "observation": ...})` in the business layer.

The agent does **not** observe the frontier's reasoning. Like a child learning from a parent, it sees what the parent does and says, but develops its own reasoning path for similar situations.

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

The `logger` and `observer` modules are shared infrastructure. The bus (`application/core/bus.py`) wraps the observer and adds automatic logging on every signal.

---

## Data Models

All shared data types live in `application/core/data.py`:

| Class | Purpose |
|---|---|
| `Channel` | Communication channel (name, credentials) |
| `Model` | AI model reference (name, provider, credentials) |
| `Thought` | Single unit of reasoning output (intent, content, tool_calls) |
| `Thinking` | Wraps a reasoning function, exposes `.reason()` |
| `Observation` | Extracted observations from conversations (facts, traits, context) |
| `Persona` | Persona configuration (id, name, model, base_model, frontier, channels, storage_dir) |

Short-term memory is per-persona and lives in the `memories` module (`memories.agent(persona).remember()`, `.recall()`, `.forget_everything()`), not in `data.py`.

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
sense (business) --> agent.given (core) --> local_model.stream (core) --> ollama (platform)
  thought.intent == "saying"    --> say (business) --> bus.order --> channels (core) --> telegram (platform)
  thought.intent == "doing"     --> act (business) --> system.execute (core) --> OS modules (platform)
  thought.intent == "consulting" --> escalate (business) --> frontier.consulting (core) --> anthropic/openai (platform)
```
