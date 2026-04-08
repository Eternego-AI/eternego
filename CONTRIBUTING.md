# Contributing to Eternego

Most AI projects are chatbots with extra steps. Eternego is an attempt to build something closer to a mind — a system that perceives, reasons, acts, and learns. If that sounds interesting, read on.

This document explains the architecture, the cognitive system, and how everything fits together. Understanding it takes about fifteen minutes. After that, you'll be able to add new capabilities, fix bugs, or propose changes without breaking the system's invariants.

---

## The Philosophy

Three beliefs shape every decision in this codebase:

**1. A business person should be able to read the code and understand what happens.** The business layer reads like English. If you need to understand what "persona creation" does, open the business function — it's a sequence of named steps with no engineering noise.

**2. Solutions should be separate from infrastructure.** The core layer solves problems. The platform layer wraps external tools. They never mix. This means we can replace Ollama with another runtime, swap Telegram for Discord, or switch encryption libraries — without touching a single line of business or core logic.

**3. The persona's intelligence should emerge from structure, not from prompts.** Instead of one massive system prompt that tries to handle everything, Eternego breaks cognition into stages. Each stage has one job. This makes the system predictable, debuggable, and improvable — you can make the persona better at *deciding* without affecting how it *answers*.

---

## Layers

```
business/    WHY — What should happen
core/        HOW — Where we engineer solutions
platform/    WHAT — What external tools provide
```

Dependencies flow downward only. Business imports core. Core imports platform. Never upward. Never sideways.

The entry point (`index.py`), the daemon (`daemon.py`), the web layer (`web/`), and the CLI (`cli/`) sit outside `application/`. They call business functions only and never touch core or platform directly.

### Entry point and daemon

Everything goes through `index.py` — the single entry point registered as the `eternego` command. It parses global flags (`--debug`, `-v`, `--port`, `--host`), bootstraps the application (logging, signals, config), and dispatches to the right handler.

The daemon (`daemon.py`) is the long-running process that wakes personas, starts the web server, and runs the heartbeat loop. It receives its config from the bootstrap — no arg parsing of its own. The OS service manager (systemd/launchd) runs `eternego daemon` from the installed copy at `~/.eternego/source/`.

### Development vs. installed service

The installer copies the project to `~/.eternego/source/` and runs the service from there. This means `eternego service start` runs the **installed** copy, not your working tree.

For development, run the daemon directly from the repo:

```bash
python index.py --debug daemon
```

This uses your live source code and shows debug output in the terminal. When you're happy with a change, re-run the installer to update the installed copy.

CLI service commands (`cli/service.py`) manage the OS service. `eternego service start --debug` generates the unit file with the right flags and starts it. Other commands (`env`, `pair`) go through the same bootstrap and call business functions directly.

### Why this matters

When you add a feature, you always know where to put things:

- "The persona should be able to set reminders" → that's a **business** question (what should happen) backed by a **meaning** (how the pipeline handles it)
- "We need to parse iCal format" → that's a **platform** capability (what a tool provides)
- "Reminders should check if the time conflicts with existing events" → that's **core** logic (how we solve the problem)

If you're ever unsure where something goes, ask: "Is this a business rule, an engineering solution, or a tool capability that is portable?" The answer tells you the layer.

---

## How We Work

Always top-down:

**1. Write the business spec first.** Define what the feature does, then translate it into a business function. The function should be self-documenting. Add `bus.propose` at the start, `bus.broadcast` at the end, and calls to core functions in between.

**2. Add core signatures only for what business asked for.** If the business spec calls `local_inference_engine.check(model)`, add `check(model)` to the core module. Never add functions speculatively.

**3. Implement core functions.** This is where you solve the problem — what steps are needed, what platform capabilities to use, how to combine them. Every core function starts with a log and uses platform modules for all infrastructure.

**4. Add platform functions only for what the tool provides.** If Ollama has `GET /api/tags`, the platform module has `get()`. If Ollama doesn't have a "get default model" concept, the platform module doesn't have `get_default_model()` — that logic lives in core.

---

## The Business Layer

Every business function is `async`, returns `Outcome[T]`, starts with `bus.propose`, and ends with `bus.broadcast`. It catches domain exceptions from core and returns user-friendly messages. It never contains engineering logic.

### Module Structure

Business modules are packages where each function lives in its own file, with the filename matching the function name. The `__init__.py` uses dynamic discovery — add a file, it's automatically available.

```
business/
├── __init__.py
├── outcome.py
├── environment/
│   ├── __init__.py        ← dynamic import (importlib/pkgutil)
│   ├── check_channel.py   ← one function: check_channel()
│   ├── check_model.py
│   ├── pair.py
│   ├── prepare.py
│   └── ready.py
├── persona/
│   ├── __init__.py
│   ├── create.py
│   ├── find.py
│   ├── wake.py
│   └── ...                ← 24 functions, one per file
└── routine/
    ├── __init__.py
    └── trigger.py
```

All imports go at file level, never inside functions. This convention also applies to `core/models/` and `core/brain/mind/conscious/` and `core/brain/mind/subconscious/`.

### Signals

The bus carries intent and results through the system:

| Method | Signal | Purpose |
|---|---|---|
| `bus.propose` | Plan | Announce intent before action |
| `bus.broadcast` | Event | Announce result after action |
| `bus.share` | Message | Share information passively |
| `bus.ask` | Inquiry | Request input from subscribers |
| `bus.order` | Command | Command an action, expect signals back |

Every business function sends at least a propose and a broadcast. This makes the system observable — you can trace exactly what happened and why.

### Error Handling

Errors flow upward in three steps:

1. **Platform** raises raw errors (`URLError`, `OSError`, etc.)
2. **Core** catches platform errors and raises domain exceptions (`InstallationError`, `EngineConnectionError`)
3. **Business** catches domain exceptions and returns user-friendly `Outcome` with a broadcast

Important: don't add try/catch to business specs before implementing core. Build downward first — see what breaks, define domain exceptions, then come back up and handle them.

---

## The Core Layer

Core functions exist because a business spec needs them. They start with a log, use platform modules for infrastructure, never send signals, and never return `Outcome`. They return data or raise exceptions.

The core layer is where engineering lives. If you need to combine three platform calls, add retry logic, validate data, or make a decision — it goes here.

---

## The Platform Layer

Platform modules expose what external tools actually offer. Nothing invented. Nothing wrapped beyond what the tool provides. They are portable across projects and contain no Eternego-specific logic.

If you can imagine copy-pasting a platform module into a completely different project and having it work — you've written it correctly.

The `OS` module is a single system-agnostic module that handles all OS-specific operations: shell execution, program installation, secret storage (keyring), and hardware detection. The application never deals with OS differences directly — `OS.py` dispatches internally per platform. Secrets are cached in memory (write-through to the OS keyring) so repeated reads don't hit the keyring service.

---

## The Cognitive System

This is the heart of Eternego. Understanding it is essential for most contributions.

### The Core Idea

Most AI systems work like this: user sends message → model generates response → done. Eternego works differently. It treats every interaction as something to be *understood*, *categorized*, *responded to*, *acted upon*, and *concluded*. Five distinct stages, each with a clear purpose.

This means a persona can handle a reminder request differently from a coding question differently from casual chat — not because of prompt engineering, but because each type of interaction is literally a different code path.

### Data Model

Four types form a cognitive graph:

```
Signal → Perception → Thought
                        ↓
                      Meaning
```

- **Signal** — an atomic message (user, assistant, or system) with a timestamp. The smallest unit.
- **Perception** — a group of related signals forming a conversation thread. Identified by an *impression* — a short description of what this thread is about.
- **Meaning** — a Python class that defines how to handle a type of interaction. This is where behavior lives.
- **Thought** — a perception paired with a meaning. The cognitive work unit that flows through the pipeline.

Think of it this way: signals are words, perceptions are conversations, meanings are skills, and thoughts are "I'm having this conversation and I know how to handle it."

### The Pipeline

The mind runs a continuous loop of six stages:

```
recognize → realize → understand → acknowledge → decide → conclude
```

Each stage has a clear entry condition. A thought can only be in one stage at a time:

| Stage | What Happens | Entry Condition |
|-------|-------------|----------------|
| **recognize** | Experienced cognition: try to route, understand, and reply in one call | Unattended signals exist |
| **realize** | Route each signal to a conversation thread (perception) | Unattended signals after recognize |
| **understand** | Match the thread to a meaning, creating a thought | Perception with no thought |
| **acknowledge** | Generate a response to the person | Thought is new, meaning has `reply` |
| **decide** | Extract structured data, execute actions | Meaning has `path`, acknowledge is done |
| **conclude** | Confirm the result to the person | Thought is processed but not wrapped up |

After each stage, the clock checks if new signals arrived. If so, it restarts from `recognize`. This ensures the persona is always responsive — it never gets stuck processing while you're waiting.

Each conscious function receives its capabilities as callbacks (`identity_fn`, `say_fn`, `express_thinking_fn`) from the Ego — it never imports channels or gateways directly.

### Meanings: Where Behavior Lives

A Meaning is a Python class with methods that map to pipeline stages. This is the most important abstraction in the system.

```python
class WeatherForecast(Meaning):
    name = "Weather Forecast"

    def description(self):
        return "The person wants to know the weather for a location and time."

    def reply(self):
        return "Acknowledge briefly that you will check the weather."

    def clarify(self):
        return (
            "The weather lookup failed. Look at the error, explain what "
            "went wrong, and ask the person to clarify the location or date."
        )

    def path(self):
        return (
            "Extract the weather request from what the person said.\n"
            'Return JSON: {"tool": "OS.execute_on_sub_process", "command": "curl ..."}\n'
        )

    def summarize(self):
        return "Share the forecast naturally — temperature, conditions, anything notable."
```

Each method serves one pipeline stage:

- **`description()`** → used by `recognize` and `understand` to match a conversation to this meaning
- **`reply()`** → used by `acknowledge` to generate the first response
- **`clarify()`** → used by `acknowledge` when retrying after an error
- **`path()`** → used by `decide` to extract structured data and determine actions
- **`summarize()`** → used by `conclude` to confirm results
- **`run()`** → executes the action (default dispatches tool calls; override for custom logic)

**Critical pitfall:** The output of `reply()` becomes visible to `decide()`. Never ask the model to state extracted values (times, dates, names) in the reply — if it gets them wrong, the error propagates into extraction. Keep replies conversational; let `path()` handle precision.

### Adding a New Meaning

1. Create a file in `application/core/brain/mind/meanings/`
2. Define the class with the methods above
3. Register it in `meanings/__init__.py` by adding it to the `built_in()` list

That's it. The pipeline picks it up automatically. Your new meaning will be available in the next recognition cycle.

### Escalation: Learning at Runtime

This is where it gets interesting.

When no existing meaning matches a conversation, the recognize stage selects `Escalation`. This asks a frontier model (or falls back to the local model) to **generate a new Meaning class as Python code**.

The generated code is saved to `~/.eternego/personas/<id>/home/meanings/` and loaded immediately. The persona uses it for the current interaction and keeps it forever.

The escalation prompt teaches the frontier model everything about the pipeline — what each method does, the pitfalls to avoid, how to structure tool calls. A well-informed frontier model produces meanings that work correctly even when executed by a weaker local model.

This means the persona's capabilities aren't fixed at deployment. They grow based on what you ask for. Day one it can chat. Day thirty it can manage your calendar, check your infrastructure, draft your emails — because you asked it to, and it taught itself how.

### The Sleep Cycle

When a persona sleeps:

1. All active thoughts finish processing
2. **learn_from_experience** — conversations are analyzed to update:
   - `person.md` — facts (timezone, relationships, preferences)
   - `traits.md` — behavioral patterns
   - `wishes.md` — goals and aspirations
   - `struggles.md` — recurring obstacles
   - `context.md` — operational context
   - `dna.md` — synthesized character description
3. Thoughts are archived to `history/`
4. **grow** — training pairs are generated from the DNA and the persona is fine-tuned locally
5. Memory is cleared for the next waking cycle

The sleep cycle is what turns a chatbot into a persona. Without it, the AI just has context. With it, the AI *becomes* the context.

### Persona Data on Disk

```
~/.eternego/personas/<id>/home/
├── config.json       — persona configuration
├── person.md         — facts about the user
├── traits.md         — observed behavioral patterns
├── wishes.md         — user's goals and aspirations
├── struggles.md      — recurring obstacles
├── context.md        — operational context
├── dna.md            — synthesized character (used for training)
├── mind/memory.json  — cognitive graph (signals, perceptions, thoughts)
├── history/          — archived conversations
├── destiny/          — scheduled reminders and events
├── notes/            — user's saved notes
├── meanings/         — learned meaning definitions (Python)
└── training/         — generated training pairs
```

All human-readable. All editable. This is intentional — the persona's knowledge should never be a black box.

---

## Code Conventions

- **Naming**: gerund intents (`saying`, `doing`, `consulting`, `reasoning`)
- **Memory access**: always through `memories.agent(persona)` — per-persona, no global state
- **Destiny entries**: `paths.save_destiny_entry()` to write, `paths.read_files_matching()` to read
- **History writes**: `paths.add_history_entry(persona_id, event, content)`
- **Signals**: propose at start, broadcast at end, every business function
- **Exceptions**: domain-specific, defined in `exceptions.py`, caught at business layer

---

## Testing

### Running Tests

```bash
pip install git+https://github.com/Eternego-AI/test-runner.git
test-runner
```

To run a specific directory:

```bash
test-runner tests/platform
test-runner tests/core
test-runner tests/business
```

### Writing Tests

Tests are plain Python — no framework imports, no decorators. Just functions and `assert`.

```python
# tests/core/example_test.py

def test_it_does_the_thing():
    result = do_thing()
    assert result == expected
```

**Rules:**

- File names end with `_test.py`
- Function names start with `test_`
- Tests run in definition order (top to bottom)
- `async def test_*` functions are supported
- No mocking libraries — use dependency injection and platform `assert_*` functions

### Test Structure

Tests mirror the application structure. Modules with one-function-per-file have matching test directories:

```
tests/
├── platform/
│   ├── anthropic_test.py
│   ├── openai_test.py
│   └── ...
├── core/
│   ├── models/
│   │   ├── chat_test.py
│   │   ├── chat_json_test.py
│   │   └── ...
│   ├── conscious/
│   │   ├── realize_test.py
│   │   ├── understand_test.py
│   │   └── ...
│   ├── subconscious/
│   │   ├── person_identity_test.py
│   │   └── ...
│   └── channels_test.py
└── business/
    ├── environment/
    │   ├── check_model_test.py
    │   └── ...
    ├── persona/
    │   ├── create_test.py
    │   └── ...
    └── routine/
        └── trigger_test.py
```

### Testing Platform Functions

Each platform module with network calls has built-in `assert_*` functions that spin up a local HTTP server, redirect the module to it, and let you control the response:

```python
from application.platform import ollama

def test_post_sends_correct_payload():
    ollama.assert_post(
        run=lambda: ollama.post("/api/pull", {"name": "llama3"}),
        validate=lambda r: assert r["body"]["name"] == "llama3",
        response={"status": "success"},
    )
```

Available: `ollama.assert_post/get/delete/call`, `anthropic.assert_chat/chat_json/call`, `openai.assert_chat/chat_json/call`, `telegram.assert_send/get_me/typing_action/call`. For OS keyring isolation, set `OS._secret_cache_only = True` in tests.

### Testing Core and Business Functions

Core functions that use the local model are tested by redirecting ollama to a local server:

```python
from application.platform import ollama

def test_get_default_model():
    result = {}
    ollama.assert_get(
        run=lambda: capture(result, local_inference_engine.get_default_model()),
        response={"models": [{"name": "llama3"}]},
    )
    assert result["value"] == "llama3"
```

Business spec tests verify the Outcome — not internals. Tests that create personas use `OS._secret_cache_only = True` to avoid hitting the real OS keyring:

```python
from application.core.data import Model, Channel
from application.platform import OS

def test_create_succeeds():
    OS._secret_cache_only = True
    result = with_fake_ollama(lambda: asyncio.run(spec.create(
        name="TestBot",
        thinking=Model(name="llama3"),
        channel=Channel(type="web", credentials={}),
    )))
    assert result.success, result.message
```

### What NOT to Test

- **Bridges** — thin wrappers around stdlib (e.g. `pathlib`, `shutil`)
- **Obvious code** — simple if/elif, direct passthrough
- **Prompts** — prompt content is validated by reading the code and checking debug logs, not by assertion
- **Fine-tuning** — requires GPU and model downloads

### When to Write Tests

Write tests to catch errors, not to prove obvious code works. If there's real logic that could break — transformation, parsing, state management, error handling — test it. If it's a one-liner bridge, skip it.

---

## Where to Start

**Want to add a new capability?** Write a Meaning. Start with the `WeatherForecast` example above, look at existing meanings in `application/core/brain/mind/meanings/`, and follow the pattern.

**Want to improve how the persona learns?** Look at the sleep cycle in core — specifically `learn_from_experience` and `grow`. This is where observation extraction and training data generation happen.

**Want to add a new communication channel?** The platform layer has channel modules. Add a new one following the Telegram pattern, then wire it up in core.

**Want to improve the pipeline itself?** Each stage is a separate file in `application/core/brain/mind/conscious/`. They're independently testable and modifiable.

**Found a bug?** Open an issue with the stage name (recognize/realize/understand/acknowledge/decide/conclude) if it's pipeline-related. This helps us triage fast.
