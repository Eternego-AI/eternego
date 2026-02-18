# Eternego — Claude Code Instructions

## What This Project Is

Eternego creates AI personas that live on the person's hardware, learn from every interaction, and are never locked into any vendor. The persona's knowledge is stored as human-readable files that can be applied to any model.

## Documentation

Read these documents before making changes:

- `README.md` — Business specifications (what the system does)
- `architecture.md` — Layer principles, cognitive architecture, patterns, and rules
- `implementation.md` — Technical solutions for each spec
- `appendix.md` — Data formats, prompts, LoRA workflow, permission storage

**Appendix note:** `appendix.md` is up to date. It covers data formats, prompts, LoRA workflow, permission storage, and directory structure that match the current codebase.

## Architecture Rules

### Three layers, dependencies flow down only

```
business/    WHY — reads like the README, calls core
core/        HOW — engineering, calls platform
platform/    WHAT — thin wrappers around external tools
```

Business imports core. Core imports platform. Never upward. The service entry point (`service.py`), the web layer (`web/`), and the CLI (`cli/`) sit outside `application/` and only call business.

### Business layer conventions

- Every function is `async`, returns `Outcome[T]`
- Starts with `bus.propose`, ends with `bus.broadcast`
- Catches domain exceptions, returns user-friendly messages
- Never contains engineering logic — that belongs in core
- Docstring comes from the README spec description

### Core layer conventions

- Every function starts with `logger.info`
- Raises domain exceptions from `application/core/exceptions.py`
- Never sends signals (no bus calls)
- Never returns `Outcome` — returns data or raises
- Uses platform modules for all infrastructure — never imports external libraries directly

### Platform layer conventions

- Exposes only what the external tool provides
- No project-specific logic
- Portable across projects

## Cognitive Architecture

The interaction system uses a cognitive model. Understand this before touching Spec 7 code.

### Flow

```
sense → agent.given(persona, stimulus) → think.reason() → yields Thought objects
  thought.intent == "saying"     → channels.send → memories.agent(persona).remember(communicated)
  thought.intent == "doing"      → system.is_authorized → system.execute → memories.agent(persona).remember(result)
  thought.intent == "consulting"  → escalate spec → frontier.consulting(persona) → memories.agent(persona).remember(observation)
  thought.intent == "reasoning"   → bus.share (internal, not shown to person)
```

### Key classes (application/core/data.py)

- `Thought(intent, content, tool_calls)` — single unit of reasoning output
- `Thinking(reason_by)` — wraps any async generator, exposes `.reason()`

Short-term memory is in `memories` module: `memories.agent(persona).remember()`, `.as_messages()`, `.as_transcript()`, `.forget_everything()`.

### Fluent API

```python
# Local model thinking
think = agent.given(persona, {"type": "stimulus", "role": "user", "content": prompt})
async for thought in think.reason():
    ...

# Frontier model thinking — same pattern
async for thought in frontier.consulting(persona, prompt).reason():
    ...
```

### Tag detection in agent.reason()

- `<think>...</think>` → reasoning intent
- `<escalate>...</escalate>` → consulting intent
- Tool calls → doing intent
- Plain text → saying intent

### Memory vs History

- **Memory** — short-term, in-process, per persona. Accessed via `memories.agent(persona).remember()`, `.as_messages()`, `.as_transcript()`, `.forget_everything()`.
- **History** — long-term, on disk (`history/` directory). Persists across sessions. Used for oversight, control, and consolidated conversation storage.

### Memory document types

| Type | Created by | Contains |
|---|---|---|
| `stimulus` | `agent.given()` (writes via memories) | role, content, channel |
| `say` | `agent.reason()` internally (writes via memories) | content |
| `act` | business/frontier: `memories.agent(persona).remember()` | tool_calls, result |
| `observation` | business escalate: `memories.agent(persona).remember()` | frontier conversation (minus reasoning) |
| `communicated` | business sense/escalate/reflect/predict: `memories.agent(persona).remember()` | channel, content |

### Action loop

Inside `agent.py`'s `_reason()` closure (the function wrapped by `Thinking`), a `while True` loop rebuilds messages from `memories.agent(persona).as_messages()` and re-streams from the local model after each tool execution. When a cycle produces no tool calls, the loop breaks. This means the agent can chain tool calls naturally — think, act, see result, think again — without the business layer needing to re-call `sense`.

### Escalation

Local model wraps in `<escalate>` tags → frontier streams via anthropic/openai platform modules → thoughts routed through same channels.send/system.execute pattern → frontier reasoning is NOT observed (agent develops its own reasoning path).

## Module Map

### Business (application/business/)

| Module | Functions |
|---|---|
| `environment.py` | prepare, check_model |
| `persona.py` | agents, find, find_by_channel, create, migrate, feed, grow, equip, chat, sense, escalate, reflect, predict, oversee, control, write_diary, sleep, start, stop |
| `outcome.py` | Outcome dataclass |

### Core (application/core/)

| Module | Role |
|---|---|
| `agent.py` | given(), initialize(), embody(), build(), identity CRUD, knowledge(), sleep(), save_training_set(), wake_up(), personas(), find() |
| `person.py` | bond(), facts/traits CRUD |
| `dna.py` | make(), read(), evolve() — persona DNA lifecycle |
| `instructions.py` | read(), give(), add() — persona operating instructions |
| `skills.py` | equip(), shelve(), summarize(), names(), delete() — persona skill documents |
| `history.py` | start(), entries(), recall(), delete(), consolidate() — long-term conversation history |
| `transcripts.py` | as_list(), extract() — conversation transcript parsing and extraction |
| `frontier.py` | allow_escalation(), consulting(persona, prompt) → returns Thinking, respond() |
| `local_model.py` | stream() async generator, observe(), study(), cluster(), assess_skill(), generate_encryption_phrase(), respond() |
| `models.py` | generate_name() |
| `local_inference_engine.py` | is_installed(), install(), pull(), check(), get_default_model(), copy(), delete(), fine_tune() |
| `bus.py` | Signal dispatch: propose, broadcast, share, ask, order |
| `system.py` | is_authorized(), execute(), is_installed(), install(), save/get_phrases(), make_rows_traceable() |
| `data.py` | Channel, Model, Thought, Thinking, Observation, Gateway, Persona |
| `memories.py` | agent(persona) → remember(), as_messages(), as_transcript(), forget_everything() — per-persona short-term memory |
| `paths.py` | agents_home(), agent_identity(agent_id) |
| `prompts.py` | BASIC_INSTRUCTIONS, ESCALATION, EXTRACTION, EXTRACTION_FROM_DNA, SKILL_ASSESSMENT, RECOVERY_PHRASE, SLEEP, DNA_SYNTHESIS, CONSOLIDATION, FRONTIER_IDENTITY, REFLECTION, PREDICTION, extraction(), extraction_from_dna(), sleep(), dna_synthesis(), consolidation(), reflection(), prediction() |
| `observations.py` | effect() — applies observations (facts, traits, context) to persona files |
| `exceptions.py` | All domain exceptions (includes ChannelError) |
| `diary.py` | open_for(), open(), record() |
| `external_llms.py` | read() — parses OpenAI/Anthropic exports |
| `channels.py` | matches(), send(), assert_receives(), listen() — returns Gateway |
| `gateways.py` | of(persona) → add(), close(), close_all(), is_active() — per-persona gateway registry |

### Web (web/)

| Module | Role |
|---|---|
| `app.py` | FastAPI app, mounts all routers |
| `requests.py` | Pydantic models: Message, ChatRequest, PersonaCreateRequest, PersonaMigrateRequest, PersonaControlRequest |
| `socket.py` | ConnectionManager (broadcast to all WS clients), on_signal subscriber, _safe() serializer |
| `routes/openai.py` | GET /v1/models, GET /v1/models/{id}, POST /v1/chat/completions |
| `routes/pages.py` | GET /dashboard, GET /dashboard/persona/{id}, GET /dashboard/persona/{id}/chat |
| `routes/api.py` | POST /api/persona/create, POST /api/persona/migrate, POST /api/persona/{id}/control |
| `routes/websocket.py` | WebSocket /ws — streams all bus signals to connected browser tabs |
| `templates/base.html` | Layout, Tailwind CDN, WebSocket client, modal utilities |
| `templates/pages/dashboard.html` | Persona grid, live signal feed per card, create/migrate modals |
| `templates/pages/persona.html` | Oversight sections (Person, Traits, Skills, Agent, History) with per-item delete |
| `templates/pages/chat.html` | Chat UI — POSTs to /v1/chat/completions with full conversation history |
| `templates/components/persona_card.html` | Card with status orb, signal feed, settings and chat icon links |
| `templates/components/create_modal.html` | Create persona form — POSTs to /api/persona/create |
| `templates/components/migrate_modal.html` | Migrate persona form — POSTs to /api/persona/migrate |
| `templates/components/section_card.html` | Oversight section card shell with entry list |
| `templates/components/entry.html` | Single oversight entry with two-step inline delete confirmation |

### CLI (cli/)

| Module | Role |
|---|---|
| `main.py` | `eternego` entry point: daemon, service start/stop/restart/status/logs, env check/prepare |

### Platform (application/platform/)

| Module | Wraps |
|---|---|
| `ollama.py` | Ollama HTTP API (get, post, delete, stream_post) |
| `anthropic.py` | Anthropic Messages API streaming + export parsing |
| `openai.py` | OpenAI Chat API streaming + export parsing |
| `telegram.py` | Telegram Bot API (send, poll, is_mentioned) |
| `filesystem.py` | File/directory operations |
| `crypto.py` | Key derivation, encryption, hashing |
| `datetimes.py` | Date/time operations (now, iso_8601, stamp, date_stamp, from_stamp) |
| `logger.py` | Structured logging |
| `observer.py` | Pub/sub signal system (Signal, Plan, Event, Message, Inquiry, Command) |
| `OS.py` | OS detection |
| `linux.py`, `mac.py`, `windows.py` | OS-specific shell and secure storage |
| `git.py` | Git operations (init, add, commit) |
| `lora.py` | LoRA fine-tuning and training data formatting via Unsloth (lazy imports) |

## Current State of Specs

### Implemented:
- Spec 1: Environment Preparation
- Spec 2: Persona Creation (with escalation instruction, per-persona model copy)
- Spec 3: Persona Migration (with per-persona model copy)
- Spec 4: Persona Feeding / Growth
- Spec 5: Persona Oversight
- Spec 6: Persona Control
- Spec 11: List Personas (agents)
- Spec 12: Find Persona by Channel (find_by_channel)
- Spec 7a: Chat (API conversation, text in/text out)
- Spec 7b: Sense (reactive loop)
- Spec 7d: Escalate (frontier routing with observation)
- Spec 7e: Reflect (reflection prompt after each sense cycle)
- Spec 7f: Predict (prediction prompt for proactive behavior)
- Spec 8: Persona Equipment (shelve, summarize, grow)
- Spec 9: Persona Diary
- Spec 10: Persona Sleep (consolidate memory to history, synthesize DNA, generate training from DNA, LoRA fine-tuning, wake up)
- History lifecycle: short-term memory flushed to `history/` via `history.consolidate()` — clusters transcript by topic, extracts observations per cluster, writes each cluster as a history file

### Implemented (continued):
- Spec 13: Persona Start (open all channel gateways, listen via threads; polling errors logged via on_error callback in core)
- Spec 14: Persona Stop (close all channel gateways)
- Spec 15: Find Persona (by ID, used by web API)
- Service entry point (`service.py`) — always starts web server (even with no personas); starts predict loop and gateways only when personas exist; web task errors surface via done_callback
- Web layer (`web/`) — FastAPI server with Jinja2 templates (Tailwind CDN):
  - OpenAI-compatible API: `GET /v1/models`, `GET /v1/models/{id}`, `POST /v1/chat/completions`
  - Dashboard: `GET /dashboard` — per-persona cards with live WebSocket signal feed, Create and Migrate modals
  - Persona detail: `GET /dashboard/persona/{id}` — 5 oversight sections (Person, Traits, Skills, Agent, History) with inline two-step delete confirmation
  - Chat: `GET /dashboard/persona/{id}/chat` — full chat UI using the OpenAI-compatible API
  - Internal API: `POST /api/persona/create`, `POST /api/persona/migrate`, `POST /api/persona/{id}/control`
  - WebSocket: `/ws` — broadcasts all bus signals to connected browser tabs
- CLI (`cli/`) — `eternego` command installed via `pyproject.toml`: `daemon`, `service`, `env` subcommands
- Install scripts (`install.sh`, `install.ps1`) — one-command setup for Linux/macOS/Windows, registers system service
- Windows platform: `winget` used for Ollama and Git installation; `pywin32` added as conditional platform dependency

### Not started:
- Circuit breaker for continuous tool failures

## Code Style

- Naming: gerund intents ("saying", "doing", "consulting", "reasoning")
- Memory access: always through `memories.agent(persona).remember()`, `.as_messages()`, `.as_transcript()`, `.forget_everything()` — per-persona, no global memory
- All feedback (delivery confirmation, tool results, observations) goes through `memories.agent(persona).remember()` from business or frontier
- Disk-based history listing: `history.entries(persona)` (long-term, on disk)
- Model naming: `models.generate_name(base_model, persona_id)` — used in create, migrate, sleep
- Instructions: split files under `instructions/` dir, joined by `instructions.read(persona)`
- Signals: plan at start, event at end, every business function
- Exceptions: domain-specific, defined in `exceptions.py`, caught at business layer
