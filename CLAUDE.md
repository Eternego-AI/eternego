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

The interaction system uses a cognitive model. Understand this before touching any brain/abilities code.

### Flow

```
persona.hear (business) → brain.reason (core, background task)
  → local_model.respond → parse JSON response
    → dispatch to ability functions (say, act, escalate, ...)
      → ability returns Prompt → appended to messages, loop continues
      → ability returns None  → loop continues silently
  → no prompts returned → loop breaks
  → history.persist
```

### Brain and Abilities

The brain (`core/brain.py`) builds a system prompt, calls the local model, parses the JSON response, and dispatches to ability functions. It runs as a background task — never blocks the caller.

Abilities (`core/abilities.py`) are plain `async` functions decorated with `@ability(description, order)`. Each receives `(persona, thread, items)` and returns a `Prompt` to feed back into the next cycle, or `None` to stop.

**Abilities that return `None` always run their body via `processes.run_async`** — fire and forget, fully isolated from the reasoning loop.

**The brain owns exception handling.** Abilities must not have top-level try/except (except the permission abilities, which have self-contained fallbacks because the permission system can fail at the filesystem level and must never crash the loop). If an ability raises, the brain converts it to a Prompt so the persona can reason about what went wrong.

### System Prompt Structure

`brain._system()` builds the system prompt with these sections in order:
1. Base instruction (JSON-only response, abilities list)
2. `## Escalation` — when and how to escalate, privacy rules
3. `## Learning About the Person` — when to use learn_identity, remember_trait, load_trait
4. `# Persona Identity` — loaded from disk if non-empty
5. `# Person Identity` — loaded from disk if non-empty
6. `# Pending Permissions` — injected only when permissions are awaiting response

### Memory vs History

- **Memory** — short-term, in-process, per persona. `memories.agent(persona)` → `remember()`, `remember_on(thread, doc)`, `private_thread()`, `filter_by(predicate)`, `as_messages(thread_id)`, `as_transcript()`, `forget_everything()`.
- **History** — long-term, on disk (`history/` directory). Persists across sessions.

### Channel Pairing

Unknown senders are gated before reaching the brain. When an unverified `chat_id` messages the bot:
1. `connections.bridge` calls `pairing.generate` → 6-char alphanumeric code stored in memory (10-minute expiry)
2. Code is sent back to the unknown sender: `"Your pairing code is: XK9R2M — run: eternego pair XK9R2M"`
3. Person runs `eternego pair XK9R2M` on the local machine → `environment.pair` → `pairing.claim` → `channels.add`
4. `channels.md` is gitignored — re-pairing required on migration (intentional trust boundary per environment)

## Module Map

### Business (application/business/)

| Module | Functions |
|---|---|
| `environment.py` | prepare, check_model, pair |
| `persona.py` | agents, find, create, migrate, feed, grow, equip, sense, escalate, reflect, predict, oversee, control, write_diary, sleep, start, stop, connect, disconnect, hear |
| `outcome.py` | Outcome dataclass |

### Core (application/core/)

| Module | Role |
|---|---|
| `brain.py` | reason(persona, thread) — background reasoning loop; _system() builds system prompt with guidance sections and pending permissions |
| `abilities.py` | say, broadcast, check_permission, ask_permission, resolve_permission, act, load_trait, load_skill, clarify, escalate, learn_identity, remember_trait, feel_struggle, update_context, schedule (stub), remind (stub), start_conversation, seek_history, replay — abilities returning None run fully async; permission abilities have self-contained fallback prompts |
| `agent.py` | initialize(), embody(), build(), identity CRUD, knowledge(), learn(), refine_context(), sleep(), save_training_set(), wake_up(), personas(), find(), remove() — `build()` writes `.gitignore` (permissions.md, channels.md); `remove()` deletes storage dir on failed creation |
| `person.py` | bond(), identified_by(), traits_toward(), add_facts(), add_traits(), refine_traits(), delete_identity(), delete_trait() |
| `pairing.py` | generate(persona_id, network_id, chat_id) → 6-char code; claim(code) → dict\|None — in-memory only, 10-minute expiry, reuses code for same pending sender |
| `channels.py` | is_verified(persona, network_id, chat_id), add(persona, network_id, chat_id), all_for(persona, network_id) — disk-backed in `channels.md`, gitignored |
| `connections.py` | verify(network), connect(persona, network, on_message), disconnect_all(persona) — bridge gates on channels.is_verified; unknown senders receive pairing code |
| `gateways.py` | of(persona) → add(gateway), find(channel), all(), close(channel), close_all() — per-persona gateway registry keyed by `type:name` |
| `dna.py` | make(), read(), evolve() — persona DNA lifecycle |
| `instructions.py` | read(), give(), add() — persona operating instructions |
| `skills.py` | equip(), shelve(), summarize(), names(), delete() — persona skill documents |
| `history.py` | start(), entries(), recall(), delete(), consolidate() — long-term conversation history |
| `transcripts.py` | as_list(), extract() — conversation transcript parsing and extraction |
| `frontier.py` | allow_escalation(), respond() |
| `local_model.py` | stream(), observe(person_struggles), study(), cluster(), assess_skill(), generate_encryption_phrase(), respond() |
| `models.py` | generate_name() |
| `local_inference_engine.py` | is_installed(), install(), pull(), check(), get_default_model(), copy(), delete(), fine_tune() |
| `bus.py` | Signal dispatch: propose, broadcast, share, ask, order |
| `system.py` | is_authorized(), execute(), is_installed(), install(), save/get_phrases(), make_rows_traceable() |
| `data.py` | Network, Channel, Message, Model, Observation(facts, traits, context, struggles — all required), Gateway, Persona |
| `memories.py` | agent(persona) → remember(), remember_on(thread, doc), private_thread(), new_thread(), current_thread(), filter_by(predicate), as_messages(thread_id), as_transcript(), forget_everything() |
| `paths.py` | agents_home(), agent_identity(agent_id), struggles(agent_id) |
| `prompts.py` | extraction(), extraction_from_dna(), sleep(), dna_synthesis(), consolidation(), reflection(), prediction(), thread_summary(), trait_refinement(existing, new_items), struggle_refinement(existing, new_items), context_refinement(existing, new_items) |
| `observations.py` | effect() — applies observations (facts, traits, context, struggles) to persona files |
| `struggles.py` | be_mindful(), identify(), refine(), identified_by(), as_list(), delete() |
| `permissions.py` | check(persona, action), pending(persona), request(persona, action, thread_id), resolve(persona, action, decision, statement) — file-backed in `permissions.md`, gitignored |
| `exceptions.py` | UnsupportedOS, InstallationError, EngineConnectionError, SecretStorageError, DiaryError, IdentityError, PersonError, ExternalDataError, FrontierError, ExecutionError, DNAError, NetworkError, NetworkVerificationRequired, PairingError |
| `diary.py` | open_for(), open(), record() |
| `external_llms.py` | read() — parses OpenAI/Anthropic exports |

### Web (web/)

| Module | Role |
|---|---|
| `app.py` | FastAPI app, mounts all routers |
| `requests.py` | Pydantic models: Message, ChatRequest, PersonaCreateRequest, PersonaMigrateRequest, PersonaControlRequest |
| `socket.py` | ConnectionManager (broadcast to all WS clients), on_signal subscriber, _safe() serializer |
| `routes/openai.py` | GET /v1/models, GET /v1/models/{id}, POST /v1/chat/completions |
| `routes/pages.py` | GET /dashboard, GET /dashboard/persona/{id}, GET /dashboard/persona/{id}/chat |
| `routes/api.py` | POST /api/pair/{code}, POST /api/persona/create, POST /api/persona/migrate, POST /api/persona/{id}/control |
| `routes/websocket.py` | WebSocket /ws — streams all bus signals to connected browser tabs |
| `templates/base.html` | Layout, Tailwind CDN, WebSocket client, modal utilities |
| `templates/pages/dashboard.html` | Persona grid, live signal feed per card, create/migrate modals |
| `templates/pages/persona.html` | Oversight sections (Person, Traits, Struggles, Skills, Agent, History) with per-item delete |
| `templates/pages/chat.html` | Chat UI — POSTs to /v1/chat/completions with full conversation history |
| `templates/components/persona_card.html` | Card with status orb, signal feed, settings and chat icon links |
| `templates/components/create_modal.html` | Create persona form — POSTs to /api/persona/create |
| `templates/components/migrate_modal.html` | Migrate persona form — POSTs to /api/persona/migrate |
| `templates/components/section_card.html` | Oversight section card shell with entry list |
| `templates/components/entry.html` | Single oversight entry with two-step inline delete confirmation |

### CLI (cli/)

| Module | Role |
|---|---|
| `main.py` | `eternego` entry point: daemon, service start/stop/restart/status/logs, env check/prepare, pair \<code\> |

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
- Spec 2: Persona Creation (with escalation instruction, per-persona model copy; `struggles.be_mindful()` called alongside `dna.make`, `history.start`, `person.bond`)
- Spec 3: Persona Migration (with per-persona model copy)
- Spec 4: Persona Feeding / Growth
- Spec 5: Persona Oversight
- Spec 6: Persona Control
- Spec 11: List Personas (agents)
- Spec 7a: Chat (API conversation, text in/text out)
- Spec 7b: Sense (reactive loop)
- Spec 7d: Escalate (frontier routing with observation)
- Spec 7e: Reflect (reflection prompt after each sense cycle)
- Spec 7f: Predict (proactive prediction — reads known struggles via `struggles.identified_by()` and skill names via `skills.names()`, passes both to `prompts.prediction()`; the persona reasons about known struggles and skill gaps and may propose acquiring skills or building solutions, then initiates a conversation with the person for confirmation)
- Spec 8: Persona Equipment (shelve, summarize, grow)
- Spec 9: Persona Diary
- Spec 10: Persona Sleep (consolidate memory to history, synthesize DNA, generate training from DNA, LoRA fine-tuning, wake up)
- History lifecycle: short-term memory flushed to `history/` via `history.consolidate()` — clusters transcript by topic, extracts observations per cluster (including struggles), writes each cluster as a history file
- Struggles system: `struggles.py` manages `person-struggles.md` per persona; extracted during consolidation via `local_model.observe(person_struggles=...)`; accumulated at `observations.effect()`; read during `predict` to inform proactive proposals

### Implemented (continued):
- Spec 13: Persona Start (open all channel gateways, listen via threads; polling errors logged via on_error callback in core)
- Spec 14: Persona Stop (close all channel gateways)
- Spec 15: Find Persona (by ID, used by web API)
- Service entry point (`service.py`) — always starts web server (even with no personas); starts predict loop and gateways only when personas exist; web task errors surface via done_callback
- Web layer (`web/`) — FastAPI server with Jinja2 templates (Tailwind CDN):
  - OpenAI-compatible API: `GET /v1/models`, `GET /v1/models/{id}`, `POST /v1/chat/completions`
  - Dashboard: `GET /dashboard` — per-persona cards with live WebSocket signal feed, Create and Migrate modals
  - Persona detail: `GET /dashboard/persona/{id}` — 6 oversight sections (Person, Traits, Struggles, Skills, Agent, History) with inline two-step delete confirmation
  - Chat: `GET /dashboard/persona/{id}/chat` — full chat UI using the OpenAI-compatible API
  - Internal API: `POST /api/persona/create`, `POST /api/persona/migrate`, `POST /api/persona/{id}/control`
  - WebSocket: `/ws` — broadcasts all bus signals to connected browser tabs
- Brain/Abilities system: `brain.py` reasoning loop, `abilities.py` with 19 abilities; system prompt guidance sections for escalation, person context, and pending permissions; permission abilities (check_permission, ask_permission, resolve_permission) with filesystem fallbacks; abilities returning None run fully async
- Permissions system: `permissions.py` file-backed per persona, gitignored; three abilities gate sensitive actions; pending permissions surfaced in system prompt so model recognises responses
- Channel pairing: `pairing.py` (in-memory codes) + `channels.py` (disk-backed verified list); `eternego pair <code>` CLI command; unknown senders receive code, person claims it locally
- Background refinement: remember_trait → person.refine_traits, feel_struggle → struggles.refine, update_context → agent.refine_context — all fire after immediate append, queued behind current Ollama request
- CLI (`cli/`) — `eternego` command installed via `pyproject.toml`: `daemon`, `service`, `env`, `pair` subcommands
- Install scripts (`install.sh`, `install.ps1`) — one-command setup for Linux/macOS/Windows, registers system service
- Windows platform: `winget` used for Ollama and Git installation; `pywin32` added as conditional platform dependency

### Not started:
- Circuit breaker for continuous tool failures

## Code Style

- Naming: gerund intents ("saying", "doing", "consulting", "reasoning")
- Memory access: always through `memories.agent(persona).remember()`, `.as_messages()`, `.as_transcript()`, `.forget_everything()` — per-persona, no global memory; struggles are disk-based via `struggles.identified_by()` / `struggles.identify()`, not in short-term memory
- All feedback (delivery confirmation, tool results, observations) goes through `memories.agent(persona).remember()` from business or frontier
- Disk-based history listing: `history.entries(persona)` (long-term, on disk)
- Model naming: `models.generate_name(base_model, persona_id)` — used in create, migrate, sleep
- Instructions: split files under `instructions/` dir, joined by `instructions.read(persona)`
- Signals: plan at start, event at end, every business function
- Exceptions: domain-specific, defined in `exceptions.py`, caught at business layer
