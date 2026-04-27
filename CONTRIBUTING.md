# Contributing to Eternego

The practical guide to working in this codebase. The architecture's reasoning is in the code itself — names are deliberate, layers are strict, and the conventions below are enforced.

---

## Setup

```bash
git clone https://github.com/Eternego-AI/eternego.git
cd eternego
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -e .
pip install -e .[training]          # only if you want grow / fine-tuning
```

---

## Run for development

```bash
python index.py --debug daemon
```

This runs the daemon from your live source tree (not the installed copy). `--debug` prints debug logs to the terminal. Open `http://localhost:5000` for the web UI.

If you want to run the installed copy instead: `eternego service start`.

---

## Run tests

The project ships its own test runner. Do not use pytest.

```bash
.venv/bin/test-runner                                            # all tests
.venv/bin/test-runner tests/core                                 # one directory
.venv/bin/test-runner tests/core/brain/functions/recognize_test.py
```

Conventions:
- Files end with `_test.py`
- Functions start with `test_`
- `async def test_*` is supported
- Tests that touch global state use `application.platform.processes.on_separate_process_async` and set `ETERNEGO_HOME` to a tempdir

Canonical patterns to copy:
- `tests/core/brain/functions/recognize_test.py` — cognitive function test
- `tests/business/persona/sleep_test.py` — business spec test
- `tests/platform/ollama_test.py` — platform module test

---

## Where things live

```
application/
  business/    one-function-per-file specs (async, return Outcome[T])
  core/        engineering — brain, abilities, tools, memory, paths, models
  platform/    thin wrappers around external tools (ollama, anthropic, telegram, OS)

tests/         mirrors application/
manager.py     process orchestrator — channels, routing, pairing
daemon.py      long-running process entry
index.py       CLI entry
web/           web UI + HTTP routes
cli/           CLI subcommands
```

Dependencies flow down only: business imports core, core imports platform. Never upward, never sideways. The entry point, daemon, web layer, CLI, and manager sit outside `application/` and only call business.

---

## Where to add things

| What you're adding | Where it goes |
|---|---|
| A business spec (one use case) | `application/business/<area>/<name>.py` — one function per file, async, returns `Outcome[T]`, name matches filename |
| A platform tool (callable by the persona from a meaning) | New `@tool("description")` function in `application/platform/<module>.py` |
| An ability (one-shot named operation) | `application/core/abilities/<name>.py` with `@ability("description", requires=...)`. Use `requires=lambda persona: ...` if it depends on a persona capability (vision, frontier model) |
| A meaning (situation the persona handles) | `application/core/brain/meanings/<name>.py` with a `Meaning` class exposing `intention()` and `path()` |
| A channel (Telegram-like) | New `application/platform/<channel>.py` matching the Connection interface (`open_gateway`, `close_gateway`, `send`, `typing`, `stop`). Add a subscriber in `manager.Agent.start` |
| An LLM provider | OpenAI-compatible: just set `base_url` in the persona config. New wire protocol: `application/platform/<name>.py` and route in `application/core/models/chat.py` and `chat_json.py` |
| A cognitive stage | `application/core/brain/functions/<stage>.py`, signature `async def <stage>(living: Living) -> list`, append to the cycle in `application/core/brain/mind.py` |

---

## How to fix a bug

1. **Reproduce.** Persona id, model, the message or signal that triggered it. If you can't reproduce locally, open an issue with those three before guessing.
2. **Find the layer.**
   - Wrong action emitted? → `application/core/brain/functions/`
   - Wrong action executed? → `application/core/brain/clock.py` executor or the tool/ability
   - Channel didn't deliver? → `manager.py` or `application/platform/<channel>.py`
   - Memory didn't persist? → `application/core/brain/memory.py`
   - Health check did the wrong thing? → `application/business/persona/health_check.py`
3. **Write the test first** when you can. Per-function tests in `tests/core/brain/functions/` are the easiest entry — they construct a real Living with mocked model responses.
4. **PR** with what the bug was, what reproduces it, what fixes it.

Logs live at `~/.eternego/logs/`. Each persona's health observations live at `~/.eternego/personas/<id>/home/health.jsonl`.

---

## Conventions

Enforced. If code contradicts a rule below, the code is wrong.

- **One function per file** in business. Filename matches function name. `__init__.py` uses dynamic discovery via `pkgutil` / `importlib`.
- **All imports at file level.** No function-scoped imports except for genuine circular-import avoidance (rare).
- **Paths come from `application/core/paths.py`.** Never hardcode filenames or compute paths inline.
- **No helpers.** Explicit repetition beats premature abstraction. Especially: no `_*` private helpers that exist to dedupe a few lines. Write them twice.
- **No backwards-compat shims.** When you change something, update the callers.
- **Comments are rare.** A comment should explain *why*, never *what*. Names are the documentation.
- **Domain exceptions** are defined in `application/core/exceptions.py`. Core raises; business catches and translates to `Outcome`.
- **Business specs** start with `bus.propose` and end with `bus.broadcast`. Cognitive functions dispatch `Tick` (Plan) on entry and `Tock` (Event) on exit.
- **Tool / ability / special results** go through `memory.add_tool_result(selector, value, status, result)`. Don't construct the call + TOOL_RESULT pair by hand.
- **Prompt examples are abstract.** Local models copy concrete in-prompt examples verbatim. Use schemas like `{"tool": "<name>", "text": "<message>"}`, never filled-in examples.
- **Editing prompts the persona reads** (identities, character, meaning paths, cognitive function prompts) is identity work. If a change would flatten the persona for engineering convenience, flag it instead of silently shaving the voice.

---

## What to watch for

- **Local model behavior is brittle.** Test prompt changes against at least one small model (qwen2.5:7b or smaller). Frontier models forgive what smaller ones won't.
- **`ego.identity` rebuilds each read** from character + situation + person files + carried context. Changing what goes into it changes every cycle stage's prompt. Mind the cache_point markers when reordering blocks.
- **Sleep is destructive of working memory.** It archives messages and replaces Pulse. Tests that depend on memory state run before sleep or after wake.
- **Cognitive failures vs infrastructure failures are surfaced differently.** `EngineConnectionError` and `BrainException` exit the cycle and dispatch `BrainFault`; `ModelError` (model returned prose, not JSON) is handled inside the stage. Don't catch them at the wrong layer.
- **`on_separate_process_async` is required for any test that mutates global state** — registries, env vars, the observer bus, model-server ports. Without isolation, tests bleed.

---

## Pull requests

- Branch off `master`
- Tests pass: `.venv/bin/test-runner`
- One logical change per PR
- Commit subject: short imperative line. Body explains *why* if non-obvious.
- Reference the issue if there is one

PRs touching `application/core/brain/` get extra scrutiny — those changes affect every persona running this code.

---

## Issues

Use the GitHub Issues tab. Include:
- What you observed
- What you expected
- How to reproduce (persona id + model + the triggering message or signal)
- Relevant log excerpts from `~/.eternego/logs/`

For cognitive bugs, name the stage (realize / recognize / learn / decide / reflect / archive). For body-level bugs, name the component (manager / agent / worker / health_check).

---

## License

MIT. By contributing you agree your contributions are licensed under MIT.
