# Contributing to Eternego

Most AI projects wrap a chat model with more prompts. Eternego tries something different — a system with a mind that has structure. It perceives, decides, acts, sleeps, and grows abilities it didn't ship with. If you want to work on it, this document explains the architecture, the conventions, and why they are what they are.

The naming deliberately mirrors human cognition — `hear`, `see`, `ego`, `identity`, `conscious`, `subconscious`, `realize`, `recognize`, `reflect`. This is not decoration. When you're wondering what something should do, the human analogue is usually the right answer. Treat the vocabulary as load-bearing.

Read time: about twenty minutes. After that, you'll know where to add things, what not to touch, and what invariants the system rests on.

---

## Three beliefs

**1. A non-engineer reading business code should understand what happens.** The business layer reads like English. A spec named `create` for a persona is a sequence of named steps, no clever abstractions, no framework magic. If you can't follow it, something is wrong.

**2. Solutions stay separate from infrastructure.** The core layer solves problems. The platform layer is a thin wrapper around external tools. They never mix. Replace Ollama, swap Telegram for Discord, drop in a new encryption library — the cognitive code should not need to know.

**3. Intelligence emerges from structure, not from one mega-prompt.** Cognition is broken into seven stages. Each stage has one job, one prompt, one schema. You can improve how the persona *decides* without touching how it *perceives*. This makes the system predictable, debuggable, and most importantly: *incrementally improvable*.

---

## Layers

```
business/    WHY — what should happen
core/        HOW — how we make it happen
platform/    WHAT — what external tools provide
```

Dependencies flow downward only. Business imports core. Core imports platform. Never upward, never sideways.

The entry point (`index.py`), the daemon (`daemon.py`), the web layer (`web/`), the CLI (`cli/`), and the process orchestrator (`manager.py`) sit outside `application/`. They call business functions only.

### Entry point and daemon

Everything starts at `index.py` — one CLI entry registered as the `eternego` command. It parses global flags, bootstraps logging/signals/config, and dispatches to the right handler. The daemon (`daemon.py`) is the long-running process. It opens the event loop, starts the manager, serves the web app, and waits on a shutdown signal.

### Development vs. installed service

The installer copies the project to `~/.eternego/source/` and runs the service from there. `eternego service start` runs the **installed** copy, not your working tree. For development, run the daemon directly from the repo:

```bash
python index.py --debug daemon
```

This uses your live source and prints debug output to the terminal.

### Where to put a new feature

Ask: "Is this a business rule, an engineering solution, or a capability a tool already provides?" The answer tells you the layer.

- "The persona should set reminders" → **business** spec + **meaning** (how the pipeline handles it)
- "We need to parse iCal" → **platform** (what a library provides)
- "Reminders should check conflicts with existing events" → **core** logic

---

## Mind and body

Eternego separates the **mind** (cognition) from the **body** (the platform machinery that carries the mind's words into the world and brings signals back). This separation is philosophical and literal.

The mind is `application/core/brain/`. It thinks. The body is the `application/platform/` layer plus `manager.py`'s Agent. It hears, sees, speaks, remembers files, connects to channels, handles retries, runs processes. When something goes wrong in the body, the mind hears it — honestly — as a signal from its own subconscious.

**Message convention.** The mind reads a standard chat transcript. `role=user` carries anything arriving from outside the persona — the person's words, tool results, body signals. `role=assistant` carries what the persona itself produced — its saying, its tool calls. The persona reads this shape because the identity prompt tells it to, so it interprets turns the way models already expect to.

Two prefixes layer meaning on top of the roles:

- **`TOOL_RESULT`** — when a tool runs, the body writes two messages: an assistant-role JSON tool call, then a user-role message beginning with `TOOL_RESULT` and naming tool, status, result. This mirrors standard chat-agent convention; the persona sees what it decided to do and what came back.
- **`Subconscious:`** — the body uses this when it needs the persona to hear a signal as its *own internal noise*, not as the person's voice. Today this is rare: wondering reports when it can't form a meaning for the current impression (`Subconscious: You tried to understand what this asks of you, and with the abilities you have, you could not.`).

Other body signals — wake/sleep triggers (`"wake up"`, `"go to sleep"`), due-destiny notifications (`"due for:\n..."`), the person's own messages — arrive as plain user-role content. Context from the conversation shape is enough for the persona to read them correctly.

---

## The cognitive cycle

The mind runs a loop of seven stages. Each stage is a function in `application/core/brain/functions/`. Each stage takes the ego (`application/core/agents.py`), one of three identity strings (see *Three identities* below), and the memory. Each returns a boolean: `True` means "done, move on," `False` means "something's not right, restart the loop from the top."

The clock (`application/core/brain/mind/clock.py`) runs the loop. The worker (`application/platform/asyncio_worker.py`) dispatches each stage as a cancellable task.

| Stage | File | Identity | Purpose |
|---|---|---|---|
| **realize** | `functions/realize.py` | perspective | Turn any image in recent memory into described text: the thinking model (observer voice) formulates vision questions, the vision model answers, the result lands in memory as a synthetic `TOOL_RESULT` so downstream stages see a normal tool-call sequence |
| **recognize** | `functions/recognize.py` | personality | Form an impression of what the moment calls for and match it to one of the persona's meanings. If no existing meaning fits, set `ability=0` and hand off to wondering |
| **wondering** | `functions/wondering.py` | teacher | Only runs when recognize left `ability=0`. Consults a teacher voice — either points back to an existing meaning recognize overlooked, or writes a brand-new meaning module and saves it to disk. The persona carries the new ability from then on |
| **decide** | `functions/decide.py` | personality | Using the chosen meaning's prompt, produce a structured plan (tool + args, or text to say) |
| **experience** | `functions/experience.py` | personality | Execute the plan: say, save notes, save destiny, run a tool. Writes both the assistant-role tool call and the user-role `TOOL_RESULT` back to memory so next cycle reads as a standard chat-agent transcript |
| **transform** | `functions/transform.py` | personality | Update the persona's distilled understanding of the person (`traits.md`, `wishes.md`, etc.) |
| **reflect** | `functions/reflect.py` | personality | Distill messages into carried-forward context; if anything is unfinished, seed the next cycle |

Stages produce output for the one after. `recognize` forms an impression and picks a meaning (or leaves `ability=0`); `wondering` backstops by finding or authoring the meaning needed; `decide` uses that meaning's prompt; `experience` acts on the plan. If any stage returns False, the tick restarts from the top — the persona sees its updated state and decides anew.

### How the loop ends

A full pass where every stage returns True exits the tick. The worker goes idle. It wakes again when a signal arrives (new message, destiny due, heartbeat nudge).

### Cognitive fault handling

Two exceptions can exit a stage cleanly:

- **`EngineConnectionError`** — the model service was unreachable, errored, or returned empty. Raised from platform, propagated through core. Tick logs a body-level fault with the provider and exits. `health_check` reads it on the next heartbeat.
- **`BrainException`** — a cognitive stage failed *after* the built-in recovery was already tried. Today this means `recognize` refused classification while `memory.meaning` was already `troubleshooting` — the forced self-diagnostic cycle didn't save it.

Either way the tick exits cleanly and the next `health_check` decides what to do. No in-loop retry. Stages that produce prose instead of JSON are handled inside the stage (see *How cognitive stages handle prose* below), not as an exception.

---

## Three identities

Each cognitive stage asks a model to think. The identity string passed as the system prompt determines *who* is thinking — the persona's own voice, a neutral observer, or an architect working on the persona's behalf. All three live in `application/core/brain/identities.py` and compose helpers from `character.py` (the stable soul) and `situation.py` (the present moment).

- **personality** — the persona's own voice. Composed of character (cornerstone, values, morals, permissions), the current situation (time, environment, today's destiny, active notes), what the persona knows about the person (identity, traits, wishes, struggles), its bearing toward them, and the carried-forward context from reflect. Used by recognize, decide, experience, transform, reflect — every stage that acts *as* the persona.
- **perspective** — a neutral observer. Not the persona; reads the persona's conversation from outside and produces whatever structured output the task needs. Used by realize to formulate vision questions. Without this voice, the thinking model wearing the persona's identity responds *as* the persona instead of producing a query.
- **teacher** — an architect who writes new abilities for the persona. Used by wondering when recognize left `ability=0`. Reads the impression, the existing meanings, the persona's built-in and platform tools, and the workspace path. Either names an existing meaning that fits (recognize simply missed it) or writes a new meaning module the persona will carry forward.

All three tell the model the same thing about conversation shape — user-role for input and tool results and body signals, assistant-role for the persona's voice and tool calls. They differ only in *who* the model is while reading.

### Character

`application/core/brain/character.py` holds the stable soul that goes inside `personality`:

- **cornerstone** — WHY the persona exists (one immutable sentence about the person and the seeing)
- **values** — WHAT it holds important (truth, care, responsibility)
- **morals** — HOW it is permitted to act (be honest, effective, helpful, curious, respectful, responsible)
- **permissions** — its agency boundary (what the person has granted; what it must ask about)

These compose in `character.shape(persona)` into a single block prefixed with the root `# You are an Eternego Persona`. The permissions text itself is rewritten by transform as the persona learns what it has been authorized to do.

### Situation

`application/core/brain/situation.py` assembles the present moment that `personality` includes:

- **time** — the current date and time
- **environment** — the OS the persona lives on
- **schedule** — today's destiny entries (reminders, events)
- **notes** — active notes the persona or the person has set aside

Three composed contexts exist: `normal` (a moment of living), `sleep` (closing — only what is kept in notes crosses the night), and `wake` (continuation — what yesterday-you chose to carry forward). `ego.current_situation` points at one of these, and `personality` renders whichever applies.

---

## Meanings

A **Meaning** is a Python class that describes one type of work the persona knows how to do. Every meaning has the same shape:

```python
class Meaning:
    def __init__(self, persona: Persona):
        self.persona = persona

    def intention(self) -> str:
        return "one-sentence description of what this meaning accomplishes"

    def prompt(self) -> str:
        return "the full prompt for decide, including tools, schema, and behavior"
```

- `intention()` is the one-line summary `recognize` shows to the model when picking a meaning. Keep it task-centered, not persona-flavored.
- `prompt()` is the full instruction shown to `decide` when this meaning is selected. It includes the task description, the tools available, and a strict JSON schema.

Built-in meanings live in `application/core/brain/meanings/`. Each file defines one class. Today's set:

- `chatting` — natural conversation
- `notifying` — alerting the person to a due event (with recurrence chaining)
- `noting` — saving notes
- `scheduling` — saving destiny entries
- `recalling` — pulling old conversations or history
- `seeing_screen` — requesting a screenshot
- `exploring_filesystem` — filesystem operations
- `troubleshooting` — the built-in self-diagnostic. The persona can remove a problematic custom meaning, clear its memory, or stop itself. Also the meaning `recognize` forces when it refuses classification, to give the persona one self-rescue attempt before the thinking model is declared faulty

Meanings are loaded once at `Memory` construction via `application/core/brain/meanings/__init__.py` and stored on the memory object. Adding a `.py` file with a `Meaning` class is enough — it's picked up by dynamic discovery.

### Critical pitfalls

**The `prompt()` string is what the model sees during `decide`.** If it contains vibes-based instructions ("presence, not action", "resist completion"), weaker models will honor the vibe and abandon the schema. Keep the schema part non-negotiable. The persona's tone belongs in the identity layer, not in the tool prompt.

**Local models treat in-prompt examples as scripts.** If you include a concrete example like `{"tool": "say", "text": "Hi Morteza"}`, smaller models will copy the example verbatim — saying "Hi Morteza" regardless of context. Use abstract schemas (`{"tool": "<name>", "text": "<message>"}`) and reserve concrete examples for cases where the shape genuinely can't be expressed abstractly.

---

## Wondering

When `recognize` forms an impression but no existing meaning fits (`ability=0`), the `wondering` stage runs next. It doesn't retry recognize; it consults a teacher.

The teacher (`functions/wondering.py`) sees only the impression — not the conversation. It also sees the full list of existing meanings, the persona's built-in and platform tools, and the persona's workspace path. It returns one of:

- `{"existing": "<name>"}` — the impression actually matches a meaning recognize overlooked. Memory is updated to point at that meaning; tick proceeds to decide.
- `{"new_meaning": "<name>", "code_lines": [...]}` — a new Meaning module is needed. The code is compiled to catch syntax errors, saved to `~/.eternego/personas/<id>/home/meanings/<name>.py`, loaded into memory via `memory.learn(name, instance)`, and used for the current moment.

The frontier model is used when configured; thinking is the fallback. If both produce unusable JSON, wondering writes a `Subconscious: You tried to understand what this asks of you, and with the abilities you have, you could not.` message to memory and returns False — the persona sees its own "I don't yet understand this" on the next tick and can address it through the normal flow.

The persona grows capabilities based on what the person actually asks for — not what the developers anticipated. This is Eternego's core bet: a persona's tool surface can't be specified up front, but it can be written when needed.

### The wondering prompt is load-bearing

The teacher prompt in `wondering.py` determines the quality of every generated meaning: naming (gerund + subject), intention phrasing, prompt structure (opening paragraph, tools, permissions classification, flow, response schema), credentials handling (secrets flow through the body, never through the mind), and coding discipline (ASCII only, no backslash line-continuation, no f-strings in intention text). Treat changes to this prompt with release-level care — every new meaning written from that point forward is shaped by it.

---

## Memory

`application/core/brain/mind/memory.py` defines the `Memory` class. One instance per persona.

Two things persist across cycles and sleep:

- `messages: list[Message]` — the recent conversation, body signals, tool results. Everything the mind saw.
- `context: str` — the distilled narrative from the last reflect. What the persona has chosen to carry forward.

Four things are ephemeral — set during one cognitive pass, never persist, never cross sleep:

- `impression: str | None` — recognize's reading of what the moment calls for (a short sentence)
- `ability: int` — the index of the chosen meaning in the current meaning list, or `0` if none fit yet
- `meaning: str | None` — the name of the meaning chosen this cycle (redundant with ability but more readable)
- `plan: dict | None` — what decide produced this cycle

The `meanings` dict (the persona's abilities) is loaded at Memory construction from disk — both built-ins from `application/core/brain/meanings/` and any persona-specific ones from `~/.eternego/personas/<id>/home/meanings/`. When wondering authors a new meaning, `memory.learn(name, instance)` adds it to the live dict immediately without rescanning.

### How reflect shapes carry-forward

Reflect distills messages into a narrative `context`. If reflect notices something unfinished, it writes a `leftover` — a short sentence naming what's still calling for attention. The leftover is stored as a **role=assistant** message: the persona's own continuation of thought, not a pseudo-user directive.

This matters. A leftover as `role=user` would look like the person said it, and recognize would match it as arriving input — creating a loop. As `role=assistant`, it's clearly the mind's own carried-forward residual.

### Sleep

When the persona sleeps, reflect runs with the sleep situation, which distills hard. Transform rewrites the identity files (`person.md`, `traits.md`, `wishes.md`, `struggles.md`, `persona-trait.md`, `permissions.md`). Messages are archived into `history/`. Memory clears for the next wake.

---

## Channels and Agents

A persona is a mind. An **Agent** (in `manager.py`) is the body that houses that mind. It owns:

- The `Ego` (the cognitive layer with worker + memory)
- A list of **gateways** — one per channel the persona is connected to
- `last_channel` — the channel the person most recently used
- Pairing codes for new channel handshakes

Each channel type (Telegram, Discord, web) has a **Connection** — one per process, shared across all personas of that type. The Connection wraps the external tool's API and dispatches signals via the observer bus.

A **Gateway** is one persona's subscription to a Connection. When a message arrives on Telegram, the Connection dispatches a `"Telegram message received"` signal with token + chat_id. Each agent's subscriber checks if the signal is for one of its gateways; if so, it calls `hear` or `see`.

### Message flow in

```
External API  →  Connection (platform)  →  signal bus  →  Agent's subscriber  →  hear/see (business)  →  Ego.receive  →  Worker wakes  →  tick
```

### Message flow out

```
decide plans a say  →  dispatch "Persona wants to say"  →  Agent's on_say  →  send on last_channel gateway  →  external API
```

If `last_channel` is None (the persona is speaking proactively, e.g. from a destiny), `on_say` fans out to all connected gateways.

### Pairing

Channels join a persona unverified. The first message on an unverified channel triggers `try_claim` — the agent sends back a pairing code. The person enters that code in the web UI; the business spec `pair` marks the channel verified and persists it. Only verified channels participate in `find_gateway` lookups.

---

## Persona lifecycle

Personas are created, migrated, woken, put to sleep, and occasionally fall sick. Their status is one of: `active`, `hibernate`, `sick`.

| State | Meaning |
|---|---|
| `active` | Manager loads the persona at startup, keeps it running |
| `hibernate` | Manager skips at startup; lifecycle is paused |
| `sick` | Set by health_check when the thinking model faults; persona shuts down, person is notified |

Key business specs in `application/business/persona/`:

- `create.py` — births a persona; writes identity, sets channels, writes initial diary
- `migrate.py` — restores from a diary + recovery phrase on a new machine; lets you change models
- `find.py` — fetch a persona by id
- `get_list.py` — list all personas
- `wake` / `sleep` cycles via `Ego.sleep_cycle` — full distillation pass and restart
- `heartbeat.py` — every minute, run health_check and react
- `health_check.py` — reads worker event log; sick/disable on fault; processes due destiny
- `hear.py` / `see.py` — receive text or image; pass to ego
- `pair.py` — verify a channel after a pairing code is claimed
- `feed.py` — ingest external history (e.g. an Anthropic export)
- `grow.py` — generate training pairs and fine-tune locally (optional)
- `export.py` — write out the persona's diary for migration

---

## Worker and health_check

The **worker** (`application/platform/asyncio_worker.py`) runs the tick and dispatches cognitive stages as cancellable tasks. It also keeps a ring-buffered event log (success/fault per stage, with provider/url/model context for infra faults) and a `loop_number` counter that bumps at the top of every while-iteration of the tick.

`health_check` is the body's periodic self-check. Every heartbeat (60s):

1. If the worker idled with an unexpected error (anything outside the clean cognitive fault channels), write a short apology message and nudge the worker back to life
2. Write an entry to `health.jsonl` — loop count, fault count, which providers faulted
3. If the thinking provider faulted → set status=sick, tell the person (including the error sample), dispatch `Persona became sick` so the manager tears the agent down
4. If the frontier or vision provider faulted → null that field on the persona config, tell the person, persist. Subsequent cycles skip that capacity until restart
5. Process any due destiny entries — write them to history, delete the source file, and seed them into memory as a plain user-role message prefixed with `due for:\n`, then nudge the worker so tick picks them up

This is how the body speaks back to the person on behalf of the mind when cognition is compromised. The mind doesn't need to know its thinking model is down — the body notices and handles it.

---

## Error model

Three exception classes in `application/core/exceptions.py`:

- **`EngineConnectionError`** — infrastructure-level failure. Raised from platform (ollama/anthropic/openai) when the model service is unreachable, errored, or returned empty. Carries the `Model` that was being used so health_check can correlate by provider.
- **`ModelError`** — the model responded, but the response structure isn't what we expected (malformed JSON, missing keys). Carries the raw response so the caller can use it as the model's actual voice rather than discarding it. Handled per-stage, never leaves the core.
- **`BrainException`** — a cognitive stage failed *after* the built-in recovery was already tried. Raised from `recognize` when the model refuses classification while `memory.meaning` is already `troubleshooting` — the forced self-diagnostic cycle was already given a chance and the model still refused. Carries the `Model` that was being used (typically `persona.thinking`) so tick logs the fault with provider attribution, and health_check marks the persona sick on the next heartbeat.

Plus domain exceptions (`IdentityError`, `SecretStorageError`, `DiaryError`, etc.) — these are defined in `exceptions.py` and caught in the business layer, translated to user-facing Outcome messages.

### How cognitive stages handle prose

When `decide` or `recognize` gets a `ModelError` (the model produced prose instead of JSON), the stage treats the prose as the persona's chosen voice, not as a parse failure:

1. The prose lands in memory as a **role=assistant** message — that's what the model said, and the conversation should reflect it.
2. The same text is dispatched as a say (via the `Persona wants to say` command) so the person hears it.
3. The stage returns `True`. The tick continues.

`recognize` has one extra hook: it is the classification gate that the rest of the cycle depends on. If it refuses once, `recognize` forces `memory.meaning = "troubleshooting"` and sets the matching ability index — so the next tick runs the built-in self-diagnostic meaning. If it refuses *again* while `memory.meaning` is already `troubleshooting`, the built-in recovery has already been tried and didn't work: it raises `BrainException(model=persona.thinking)`. Tick catches, logs a fault, and health_check marks the persona sick.

Other stages (`wondering`, `reflect`, `transform`) log a warning and return False on `ModelError` — they don't carry the persona's voice, so their failure is just "didn't succeed, try again next loop."

This approach is structurally different from retrying inline. The model's output is always preserved (no silent discard), and the decision about whether a failure is cognitive or infrastructural is made one layer up (tick + health_check), not inside the stage.

---

## Layer conventions

### Business

Every business function:

- Is `async`, returns `Outcome[T]`
- Starts with `bus.propose`, ends with `bus.broadcast`
- Catches domain exceptions and returns user-friendly Outcome messages
- Contains no engineering logic (that belongs in core)
- Is one function per file, filename matches function name
- All imports at file level, never inside functions

`__init__.py` files in business modules use dynamic discovery via `importlib`/`pkgutil`. Adding a new `.py` with an async function gets it automatically surfaced.

### Core

Every core function:

- Starts with `logger.info` or `logger.debug`
- Raises domain exceptions on failure, never returns `Outcome`
- Uses platform modules for all external interaction — never imports `requests`, `httpx`, `sqlite3`, etc. directly
- Never sends bus signals (that's business)

### Platform

Platform modules:

- Expose only what the external tool actually provides
- Contain zero project-specific logic
- Could be copy-pasted into a different project and still work
- `OS.py` is the single system-agnostic module for OS operations (shell, install, keyring, hardware)

Conscious functions receive capabilities as callbacks from Ego — they never import channels or gateways directly. This keeps the cognitive layer pure.

---

## Code conventions

- **Naming**: gerund intents for meanings and stages (`chatting`, `noting`, `recognizing`)
- **Paths**: every path comes from `application/core/paths.py`. Don't hardcode filenames or compute paths inline
- **No helpers**: prefer explicit repetition over premature abstraction. Duplicated lines are cheaper than the wrong abstraction
- **No `_*` helper functions**: if a block is worth reading twice, write it twice. This rule is hard
- **Imports at top**: no function-scoped imports
- **Comments are rare**: a comment should explain *why*, never *what*. Code names are the documentation
- **Signals**: propose at start, broadcast at end, every business function
- **Exceptions**: domain-specific, defined in `exceptions.py`, caught at the business layer
- **No backwards-compat shims**: when you change something, update callers. Don't leave deprecated paths
- **Wear the soul hat when editing cognitive prompts**: the identity, character, meanings, and brain-function prompts are the voice the model inhabits. Edit them as the model that will read them — if a change would flatten the persona for engineering convenience, flag it instead of silently shaving the voice

---

## Testing

Tests are plain Python. No framework imports, no decorators. Just functions and `assert`.

```python
# tests/core/example_test.py

async def test_it_does_the_thing():
    result = await do_thing()
    assert result == expected
```

Rules:

- File names end with `_test.py`
- Function names start with `test_`
- `async def test_*` is supported
- Tests that spin up model servers use `on_separate_process_async` to isolate state

### Running

The project ships its own test-runner CLI:

```bash
.venv/bin/test-runner              # all tests
.venv/bin/test-runner tests/core   # one directory
.venv/bin/test-runner tests/business/persona/create_test.py
```

### Testing platform functions

Each platform module with network calls has built-in `assert_*` helpers that spin up a local HTTP server, point the module at it, and let you control the response:

```python
from application.platform import anthropic

def test_chat_sends_correct_headers():
    anthropic.assert_chat(
        run=lambda url: capture(result, anthropic.chat(url, "key", "claude-haiku", [...])),
        validate=lambda r: assert r["headers"]["x-api-key"] == "key",
        response={"content": [{"text": "hi"}]},
    )
```

Available: `ollama.assert_call/chat/chat_json`, `anthropic.assert_chat/chat_json/call`, `openai.assert_chat/chat_json/call`, `telegram.assert_*`, `discord.assert_*`, `http.assert_call`.

### Testing business specs

Business spec tests verify the `Outcome`, not internals. Use `on_separate_process_async` for isolation and set `ETERNEGO_HOME` to a tempdir so nothing leaks into `~/.eternego`:

```python
async def test_create_succeeds():
    def isolated():
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ETERNEGO_HOME"] = tmp
            # ... test body
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
```

### What not to test

- Thin wrappers around stdlib (`pathlib`, `shutil`)
- Prompt *content* — prompts are validated by reading code and checking debug logs, not asserted
- Obvious passthroughs

Write tests for real logic: parsing, state transitions, error handling, branching. Not for one-liners.

---

## Where to start

**Add a new ability?** Drop a `Meaning` class in `application/core/brain/meanings/<name>.py`. The `Meaning` shape and the `intention()` / `prompt()` methods are all you need. Dynamic discovery picks it up on next Memory construction.

**Add a new channel?** Look at `application/platform/telegram.py` and `discord.py`. Implement the same Connection interface (`open_gateway`, `close_gateway`, `send`, `typing`, `stop`). Then add a subscriber in `manager.Agent.start` for the channel's signals, alongside `on_telegram_message`.

**Add a new LLM provider?** If it's OpenAI-compatible, nothing to do — set `base_url` in the Model config. If it's a new wire protocol, add a module in `application/platform/<name>.py` following `anthropic.py`'s shape, and route to it in `application/core/models/chat.py` and `chat_json.py`.

**Improve the cognitive pipeline?** Each stage is one file in `application/core/brain/functions/`. They're independently testable. The principle: schema-strict prompts, honest error surfacing, no in-stage retry — prose is dispatched as the persona's say, and genuine cognitive failure is surfaced via `BrainException` from the one stage that classifies (recognize), after the forced-troubleshooting recovery cycle.

**Found a bug?** Open an issue. Include the stage name (realize/recognize/decide/experience/transform/reflect) if it's pipeline-related, or the component (manager/agent/worker/health_check) if it's body-level. This triages fast.

**Questions about conventions?** Everything in this document is enforced. If something in the code contradicts it, that's a bug — either the code or the doc is wrong. File an issue, don't work around.
