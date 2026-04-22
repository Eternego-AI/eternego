# Eternego — Claude Code Instructions

## What this project is

Eternego creates AI personas that live on the person's hardware, learn from every interaction, and are never locked to any vendor. The persona's knowledge is stored as human-readable files (diary, notes, destiny, meanings, distilled context) that can be applied to any model.

## Read these before making changes

- `README.md` — what the system does (business-facing)
- `CONTRIBUTING.md` — architecture, conventions, cognitive cycle, error model, testing

`CONTRIBUTING.md` is the source of truth for how the system is organized. Everything below is a summary — when in doubt, read CONTRIBUTING.

## Three layers, dependencies flow down only

```
business/    WHY — reads like English, calls core
core/        HOW — engineering, calls platform
platform/    WHAT — thin wrappers around external tools
```

Business imports core. Core imports platform. Never upward, never sideways. The entry point (`index.py`), the daemon (`daemon.py`), the web layer (`web/`), the CLI (`cli/`), and the process orchestrator (`manager.py`) sit outside `application/` and only call business.

## Mind and body

The mind (`application/core/brain/`) thinks. The body (`application/platform/` + `manager.py`'s Agent) carries the mind's words into the world and brings signals back. Messages follow the standard chat convention: `role=user` for anything from outside the persona (person's words, tool results, body signals), `role=assistant` for what the persona itself produced. Two prefixes layer on top:

- `TOOL_RESULT` — user-role messages following an assistant-role tool call, naming tool/status/result
- `Subconscious:` — user-role messages the body flags as the persona's own internal noise (today: wondering reporting it couldn't form a meaning)

The persona reads this shape because its identity tells it to. See CONTRIBUTING.md "Message convention" for the full rules.

## Three identities

Each cognitive stage takes one of three identity strings as its system prompt. All three live in `application/core/brain/identities.py`:

- **personality** — the persona's own voice (character + situation + person facts + carried context). Used by recognize, decide, experience, transform, reflect
- **perspective** — a neutral observer reading the conversation from outside. Used by realize to formulate vision questions without slipping into the persona's voice
- **teacher** — an architect who writes new abilities for the persona. Used by wondering when recognize left `ability=0`

## The cognitive cycle

Seven stages in `application/core/brain/functions/`, run by `clock.tick`:

```
realize → recognize → wondering → decide → experience → transform → reflect
```

Each stage is testable independently. Each returns True to advance, False to restart the tick from the top. Two exceptions exit the tick cleanly: `EngineConnectionError` (infra fault — provider unreachable/empty) and `BrainException` (recognize refused classification again while already on the troubleshooting meaning — the built-in recovery didn't save it).

When decide or recognize receive prose instead of JSON, they dispatch the prose as a say (assistant-role) rather than raising. Recognize also forces `memory.meaning = "troubleshooting"` on first refusal so the next tick runs the self-diagnostic. Only a second refusal while on troubleshooting escalates to `BrainException`.

## Business layer conventions

- Every function is `async`, returns `Outcome[T]`
- Starts with `bus.propose`, ends with `bus.broadcast`
- Catches domain exceptions from core, returns user-friendly Outcome messages
- Contains no engineering logic
- One function per file, filename matches function name, `__init__.py` uses dynamic discovery
- All imports at file level, never inside functions

## Core layer conventions

- Starts with `logger.debug` or `logger.info`
- Raises domain exceptions from `application/core/exceptions.py`
- Never sends bus signals (no `bus.*` calls)
- Never returns `Outcome` — returns data or raises
- Uses platform modules for all infrastructure — never imports external libraries directly

## Platform layer conventions

- Exposes only what the external tool provides
- No project-specific logic, no Eternego assumptions
- Portable across projects
- `OS.py` is the single system-agnostic module for all OS operations (no per-OS modules)
- Conscious functions receive capabilities as callbacks from Ego, never import channels/gateways directly

## Code style

- **Naming**: gerund intents (`saying`, `doing`, `recognizing`, `chatting`). The vocabulary mirrors human cognition deliberately — treat it as load-bearing
- **Paths**: every path comes from `application/core/paths.py`. Don't hardcode filenames or compute paths inline
- **Memory**: per-persona via `Memory(persona)` or `ego.memory`. No global memory state
- **Signals**: `bus.propose` at start, `bus.broadcast` at end, every business function
- **Exceptions**: domain-specific, defined in `exceptions.py`, caught at the business layer
- **No helpers**: prefer explicit repetition over premature abstraction. No `_*` helper functions that exist to dedupe a few lines — write them twice
- **No backwards-compat shims**: when you change something, update callers
- **Soul hat**: identity, character, meanings, and brain-function prompts are the voice the model inhabits. Edit them as the model that will read them — flag tradeoffs instead of silently flattening the voice
- **Prompt examples get copied**: local models treat concrete in-prompt examples as scripts. Use abstract schemas (`{"tool": "<name>", "text": "<message>"}`), not filled-in examples

## Testing

The project ships its own test-runner. Do not use `pytest`.

```bash
.venv/bin/test-runner               # all tests
.venv/bin/test-runner tests/core    # one directory
.venv/bin/test-runner <path>        # one file
```

Tests are plain Python. No framework, no decorators. Files end in `_test.py`, functions start with `test_`. `async def test_*` is supported. Tests that spin up model servers use `on_separate_process_async` for isolation and set `ETERNEGO_HOME` to a tempdir so nothing leaks into `~/.eternego`.
