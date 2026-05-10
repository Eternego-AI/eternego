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

The mind (`application/core/brain/`) thinks. The body (`application/platform/` + `manager.py`'s Agent) carries the mind's words into the world and brings signals back. Messages follow the standard chat convention: `role=user` for anything from outside the persona (person's words, tool results, body signals), `role=assistant` for what the persona itself produced.

`TOOL_RESULT` is the prefix on user-role messages that follow an assistant-role tool/ability call — naming tool, status, and result. Cognitive functions speak in cognitive verbs (`memory.intention(text)`, `memory.perception()`, `memory.impression(body)`, `memory.comprehension()`); memory translates those into the standard tool-call/TOOL_RESULT shape under the hood. Mechanical tools/abilities the executor actually runs go through `memory.add_tool_result(selector, value, status, result)`.

## Four alive voices

Each cognitive stage uses one of four "alive" voices. All four live in `application/core/agents.py`:

- **Ego** — the persona's own voice. Identity is rebuilt every read from character, situation, person facts, and carried context. Speaks through `persona.thinking`. Used by recognize, decide, reflect, archive.
- **Consultant** — a neutral observer. Reads the conversation from outside without slipping into the persona's voice. Reuses `persona.thinking` with a different framing. Used by realize to formulate vision questions.
- **Eye** — the persona's sight. Looks at images, reports what it sees. Uses `persona.vision` (optional).
- **Teacher** — a frontier mind that writes a new lesson when the persona expresses an intention for a kind of moment she has no procedure for. Uses `persona.frontier`. When the Teacher teaches a lesson, the persona's own thinking model translates it into the meaning prose she'll read herself next time. Called by learn (and by reflect when she crystallizes a new instruction).

## The cognitive cycle

Six stages in `application/core/brain/functions/`, run once per beat by `clock.run(living)`:

```
realize → recognize → learn → decide → reflect → archive
```

Each stage takes only `living: Living` and returns `list[Consequence]` — a declaration of mechanics for clock's executor to run. No restart-on-False. One pass through the cycle per beat. Each stage is testable independently.

Two exceptions exit the cycle cleanly: `EngineConnectionError` (provider unreachable/empty) and `BrainException` (recognize refused classification again while already on the troubleshooting meaning). Both dispatch a `BrainFault` signal that health_check reads on the next heartbeat.

When recognize or decide receive prose instead of JSON, they dispatch the prose as a say (assistant-role) rather than raising — graceful fallback for models that don't follow the schema cleanly. The cycle continues; the persona reads her own prose on the next beat and re-perceives.

## Phase

Pulse holds `phase: Phase | None` (Enum: `MORNING` / `DAY` / `NIGHT`). Phase transitions: wake → MORNING; hear/see → DAY; sleep → NIGHT.

`Pulse.hint()` returns one phase-specific system prompt appended after Ego's identity on each model call — the persona reads where she is on the day's arc every tick. Phase changes are rare and immediately trigger persona activity, so cache invalidation isn't a concern.

## Three entities — tools, abilities, meanings

Layered by what state they see. From the persona's view, tools and abilities share the `tools.<name>` namespace — the distinction lives in the codebase, not in her vocabulary.

- **Tools** (`application/platform/*.py`, `@tool`) — platform primitives. `tools.call(name, **args) → (status, result)`. Catches its own exceptions.
- **Abilities** (`application/core/abilities/*.py`, `@ability("desc", requires=...)`) — one-shot named verbs. `abilities.call(persona, name, **args)`. The optional `requires=lambda persona: bool` predicate gates per-persona availability (e.g., `look_at` requires a vision model). Surfaced under `tools.<name>` to the persona; `clock.execute` resolves names against both registries.
- **Meanings** (`application/core/brain/meanings/*.md`) — situations the persona knows how to be in. Markdown files: first H1 is the intention, body is the path prose. The persona retrieves a meaning's body via `tools.load_instruction(intention=...)` — recognize records her intention, learn matches the catalog and writes the impression, decide acts on it. Built-ins ship; custom meanings live in the persona's home `meanings/` dir alongside the originating `lessons/` file. `meanings.builtin(persona)` and `meanings.custom(persona)` load both layers.

Consequence selectors are always `tools.<name>` — clock's executor looks up `name` in the platform-tools registry first, then abilities.

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
- Cognitive functions dispatch `Tick` (Plan) on entry and `Tock` (Event) on exit; no `bus.propose`/`bus.broadcast` (those are business-side)
- Never returns `Outcome` — returns data or raises
- Uses platform modules for all infrastructure — never imports external libraries directly

## Platform layer conventions

- Exposes only what the external tool provides
- No project-specific logic, no Eternego assumptions
- Portable across projects
- `OS.py` is the single system-agnostic module for all OS operations (no per-OS modules)

## Code style

- **Naming**: gerund intents (`saying`, `doing`, `recognizing`, `chatting`). The vocabulary mirrors human cognition deliberately — treat it as load-bearing
- **Paths**: every path comes from `application/core/paths.py`. Don't hardcode filenames or compute paths inline
- **Memory**: per-persona via `Memory(persona)` or `ego.memory`. No global memory state
- **Tool results**: cognitive signals go through cognitive verbs (`memory.intention`, `memory.perception`, `memory.impression`, `memory.comprehension`); mechanical tool/ability invocations go through `memory.add_tool_result`. The wire shape (assistant call + user TOOL_RESULT) lives only inside memory
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
