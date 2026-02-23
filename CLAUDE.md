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

Business imports core. Core imports platform. Never upward. The service entry point (`service.py`), the heartbeat (`heart.py`), the web layer (`web/`), and the CLI (`cli/`) sit outside `application/` and only call business.

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

### Three Cognitive Loops

```
Thinking loop    — triggered by persona.hear or persona.nudge
Summarizing loop — triggered by persona.hear (after think) or persona.sleep
Growth loop      — triggered by persona.sleep (after summarize)
```

**Thinking** (`mind.think`): fire-and-forget background task. Builds system prompt, calls the model in a loop, dispatches to abilities.

**Summarizing** (`mind.summarize`): reflective loop over a list of threads. For each thread, asks the model to archive the conversation using the `archive` ability. Uses a reflective channel (authority="reflective").

**Growth** (`mind.grow`): synthesises DNA from history, generates per-item training pairs, fine-tunes the model, wakes up.

### Hear Flow

```
persona.hear (business)
  → memories.remember(message)
  → mind.think(persona, thread, channel)     ← background, non-blocking
  → mind.summarize(persona, thread, channel, [thread])  ← awaited
```

### Think Flow

```
mind.think (core, background task)
  → values.build(persona, channel) → system prompt filtered by channel.authority
  → mind.reason loop:
      → local_model.respond → parse JSON
        → dispatch to ability functions
          → ability returns Prompt → appended to messages, loop continues
          → ability returns None  → loop continues silently
      → no new prompts → loop breaks
```

### Sleep Flow

```
persona.sleep (business)
  → mind.summarize(persona, sleep_thread, reflective_channel, m.threads())
  → memories.forget_everything()
  → mind.grow(persona, reflective_channel)
  → write_diary(persona)
```

### Heartbeat Flow

```
heart.beat(persona) — called every 60 seconds by service.py
  → persona.live(persona, now)    ← finds destiny entries due this minute, nudges
  → routine.trigger(persona)      ← fires scheduled routines (e.g. sleep at midnight)
```

```
persona.live → paths.read_files_matching(destiny_dir, "*YYYY-MM-DD-HH-MM*.md")
  → persona.nudge(persona, "These entries are due: ...")
    → mind.think on secretary channel (private thread)
      → model uses calendar/reminder to inspect, reach_out to deliver, manifest_destiny to archive
```

### Channel Authorities

| Authority | Used by | Say allowed | Key abilities |
|---|---|---|---|
| `commander` | Telegram and other real channels | ✓ | all |
| `conversational` | Web/API chat | ✓ (OpenAI JSON format) | all |
| `reflective` | Sleep summarization | ✗ | archive |
| `secretary` | Heartbeat nudges | ✗ | calendar, reminder, schedule, remind, reach_out, manifest_destiny |

`channel.authority` is set by the caller. `values.build()` filters the abilities list shown in the system prompt to only those whose `ability_scopes` include the current authority. `mind.reason()` blocks calls to out-of-scope abilities at dispatch time too.

### Brain and Abilities

The brain package lives at `core/brain/`. Key modules:

- `mind.py` — `think()`, `reason()`, `summarize()`, `grow()`
- `values.py` — `build(persona, channel)` composes the system prompt
- `cornerstone.py` — base instruction (JSON-only, abilities list format)
- `abilities/` — package; each topic file exports decorated ability functions
- `memories.py` — per-persona in-process memory; `agent(persona)` → `AgentMemory`
- `skills/` — Python modules with `name`, `summary`, `skill(persona) -> str`

Abilities are `async` functions decorated with `@ability(description, scopes, order)`. Each receives `(persona, thread, channel, items)` and returns a `Prompt` (continue loop) or `None` (stop loop). **Abilities returning `None` always run their body via `processes.run_async`.**

**The brain owns exception handling.** Abilities must not have top-level try/except (except permission abilities, which have filesystem fallbacks). If an ability raises, `mind.reason()` converts it to a Prompt.

### System Prompt Structure

`values.build(persona, channel)` composes:
1. `cornerstone.instruction(persona)` — JSON-only response format, filtered abilities list
2. `being_persona` skill — who this persona is
3. `# Persona Context` — loaded from disk if non-empty
4. `# Person Identity` — loaded from disk if non-empty
5. `# Pending Permissions` — injected only when permissions are awaiting response

### Memory vs History

- **Memory** — short-term, in-process, per persona. `memories.agent(persona)` → `remember()`, `remember_on(thread, doc)`, `private_thread()`, `new_thread()`, `threads()`, `filter_by(predicate)`, `as_messages(thread_id)`, `forget_everything()`.
- **History** — long-term, on disk (`history/` directory). Persists across sessions. Written by `archive` ability (sleep) and `manifest_destiny` ability (heartbeat).

### Channel Pairing

Unknown senders are gated before reaching the brain. When an unverified `chat_id` messages the bot:
1. `channels.pair(persona, channel)` → 6-char uppercase hex code stored via `system.save_pairing_code()` in OS secure storage
2. Code is sent back to the unknown sender: `"Your pairing code is: XK9R2M — run: eternego pair XK9R2M"`
3. Person runs `eternego pair XK9R2M` on the local machine → `environment.pair` → `channels.save()`
4. `channels.md` format: `type:name:verified_at` — gitignored, re-pairing required on migration

## Module Map

### Root

| File | Role |
|---|---|
| `service.py` | Entry point: starts web server, persona gateways; calls `heart.beat(agent)` every 60 seconds |
| `heart.py` | `beat(persona)` — logs heartbeat, calls `persona.live` then `routine.trigger` |

### Business (application/business/)

| Module | Functions |
|---|---|
| `environment.py` | prepare, check_model, pair |
| `persona.py` | agents, find, create, migrate, feed, equip, oversee, control, write_diary, sleep, start, stop, connect, pair, hear, nudge, live |
| `routine.py` | trigger — fires routines whose HH:MM matches now; resolves spec name to `persona.py` function via `getattr` |
| `outcome.py` | Outcome dataclass |

### Core (application/core/)

| Module | Role |
|---|---|
| `brain/mind.py` | `think(persona, thread, channel)` — fire-and-forget background reasoning; `reason(persona, thread, channel, messages)` — model loop with ability dispatch; `summarize(persona, thread, channel, items)` — reflective loop over threads; `grow(persona, channel)` — DNA synthesis, training, fine-tune, wake up |
| `brain/abilities/` | Package; flat re-export via `__init__.py`. Topic files: `communication.py` (say, clarify, escalate, start_conversation, reach_out), `consent.py` (check_permission, ask_permission, resolve_permission), `system.py` (act), `knowledge.py` (load_trait, load_skill, learn_identity, remember_trait, feel_struggle, update_context), `destiny.py` (schedule, remind, calendar, reminder, manifest_destiny), `history.py` (seek_history, replay, archive), `routine.py` (list_routines, add_routine, remove_routine). Each ability decorated with `@ability(description, scopes, order)` |
| `brain/values.py` | `build(persona, channel)` — composes full system prompt; filters abilities by channel.authority |
| `brain/cornerstone.py` | `instruction(persona)` — base JSON-only instruction with abilities list |
| `brain/memories.py` | `agent(persona)` → `AgentMemory`: `remember()`, `remember_on(thread, doc)`, `private_thread()`, `new_thread()`, `threads()` → list[Thread], `filter_by(predicate)`, `as_messages(thread_id)`, `forget_everything()` |
| `brain/skills/` | Python modules with `name: str`, `summary: str`, `skill(persona) -> str`; `basics` list used by `load_skill` ability |
| `agent.py` | initialize(), embody(), build(), identity CRUD, knowledge(), learn(), refine_context(), sleep(), save_training_set(), wake_up(), personas(), find(), remove() |
| `person.py` | bond(), identified_by(), traits_toward(), add_facts(), add_traits(), refine_traits(), delete_identity(), delete_trait() |
| `channels.py` | open(persona, channel, on_message) → stop callable; send(channel, text); pair(persona, channel) → 6-char code; save(persona, channel); is_verified(persona, channel) |
| `gateways.py` | `of(persona)` → Connections; `Connections.add(channel, stop)`, `remove(channel)`, `has_channel(channel)`, `all_channels() -> list[Channel]`, `clear()` |
| `dna.py` | make(), read(), evolve() |
| `instructions.py` | read(), give(), add() |
| `skills.py` | equip(), shelve(), summarize(), names(), delete() |
| `history.py` | start(), entries(), recall(), delete(), consolidate() |
| `transcripts.py` | as_list(), extract() |
| `frontier.py` | allow_escalation(), respond() |
| `local_model.py` | stream(), observe(person_struggles), study(), cluster(), assess_skill(), generate_encryption_phrase(), respond() |
| `models.py` | generate() |
| `local_inference_engine.py` | is_installed(), install(), pull(), check(), get_default_model(), copy(), delete(), fine_tune() |
| `bus.py` | Signal dispatch: propose, broadcast, share, ask, order |
| `system.py` | is_authorized(), execute(), is_installed(), install(), save/get_phrases(), make_rows_traceable(), get_pairing_codes(), save_pairing_code() |
| `data.py` | Channel(type, name, authority="commander", credentials, verified_at, bus), Message, Model, Observation, Persona(id, name, model, base_model, version, birthday, frontier, channels), Thread(id, public), Prompt(role, content) |
| `paths.py` | Path helpers: home, persona_identity, person_identity, person_traits, context, struggles, memory, channels, skills, destiny, history, history_briefing, permissions, training_set, dna, routines, diary. Write helpers: save_as_json, save_as_binary, save_as_string, save_destiny_entry(persona_id, event, trigger, thread_id, content), add_history_entry(persona_id, event, content), add_history_briefing, add_routine, add_person_identity, add_person_traits, add_struggles, append_context, write_dna, add_training_set. Read helpers: read(path), read_history_brief, read_files_matching(persona_id, directory, pattern) → list[str] with "File: name\\ncontent" format. Other: create_home, create_directories, md_list(path, section), lines(path), delete_entry, find_and_delete_file, zip_home, unzip, copy_recursively, delete_recursively, encrypt, decrypt, clear, commit_diary, init_git |
| `prompts.py` | extraction(), extraction_from_dna(), grow(), dna_synthesis(previous_dna, person_traits, persona_context, history_briefing), consolidation(), reflection(), prediction(), thread_summary(), trait_refinement(), struggle_refinement(), context_refinement() |
| `observations.py` | effect() |
| `struggles.py` | be_mindful(), identify(), refine(), identified_by(), as_list(), delete() |
| `permissions.py` | check(persona, action), pending(persona), request(persona, action, thread_id), resolve(persona, action, decision, statement) |
| `exceptions.py` | UnsupportedOS, InstallationError, EngineConnectionError, SecretStorageError, DiaryError, IdentityError, PersonError, FrontierError, ExecutionError, DNAError, ChannelError, SkillError, HistoryError, ContextError |
| `diary.py` | open_for(), open(), record() |
| `external_llms.py` | read() |
| `context.py` | context management |

### Web (web/)

| Module | Role |
|---|---|
| `app.py` | FastAPI app, mounts all routers; registers `_on_reasoning_plan` subscriber |
| `requests.py` | Pydantic models: Message, ChatRequest, PersonaCreateRequest, PersonaMigrateRequest, PersonaControlRequest |
| `socket.py` | ConnectionManager, on_signal subscriber, _safe() serializer |
| `routes/openai.py` | GET /v1/models, GET /v1/models/{id}, POST /v1/chat/completions, DELETE /persona/{id}/chat/{thread_id} |
| `routes/pages.py` | GET /dashboard, GET /dashboard/persona/{id}, GET /dashboard/persona/{id}/chat |
| `routes/api.py` | POST /api/pair/{code}, POST /api/persona/create, POST /api/persona/migrate, POST /api/persona/{id}/control |
| `routes/websocket.py` | WebSocket /ws — streams all bus signals to connected browser tabs |
| `templates/` | Jinja2 templates: base, dashboard, persona detail, chat, components (card, modals, section, entry) |

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
- Spec 2: Persona Creation (with escalation instruction, per-persona model copy; `struggles.be_mindful()` called alongside `dna.make`, `history.start`, `person.bond`; default sleep routine added to `routines.json`)
- Spec 3: Persona Migration (with per-persona model copy)
- Spec 4: Persona Feeding / Growth
- Spec 5: Persona Oversight
- Spec 6: Persona Control
- Spec 11: List Personas (agents)
- Spec 7a: Chat (API conversation, text in/text out)
- Spec 7b: Sense (reactive loop)
- Spec 7d: Escalate (frontier routing with observation)
- Spec 7e: Reflect (reflection prompt after each sense cycle)
- Spec 7f: Predict (reads struggles via `struggles.identified_by()` and skill names via `skills.names()`; persona proposes acquiring skills or building solutions)
- Spec 8: Persona Equipment (shelve, summarize, grow)
- Spec 9: Persona Diary
- Spec 10: Persona Sleep — three-phase: `mind.summarize` (archive all threads reflectively) → `memories.forget_everything()` → `mind.grow` (DNA synthesis, per-item training, fine-tune, wake up)
- History lifecycle: short-term memory archived to `history/` via reflective summarization during sleep; `archive` ability writes per-thread history files; `manifest_destiny` ability writes destiny entries to history
- Struggles system: `struggles.py` manages `person-struggles.md`; extracted during consolidation; read during `predict`
- Brain package: `core/brain/` with `mind.py`, `values.py`, `cornerstone.py`, `memories.py`, `abilities/` package (27 abilities in 7 topic files), `skills/` package
- Abilities package: flat namespace via `__init__.py` re-exports; topic files are organisational only; reflection still works via `getattr(abilities, key)`
- Permissions system: file-backed per persona, gitignored; three abilities gate sensitive actions; pending permissions surfaced in system prompt
- Channel pairing: in-memory codes + disk-backed verified list; `eternego pair <code>` CLI command
- Background refinement: remember_trait, feel_struggle, update_context all fire via `processes.run_async`
- Heartbeat cycle: `heart.beat(persona)` called every 60 seconds; calls `persona.live` (destiny) then `routine.trigger` (routines)
- Destiny system: schedules and reminders stored as `{event}-{YYYY-MM-DD-HH-MM}-{thread_id[:8]}-{stamp}.md` files in `destiny/`; heartbeat finds due entries by glob pattern; `manifest_destiny` ability archives and deletes them; no separate destiny module — all logic in `paths.py` and abilities
- Routine system: `routines.json` per persona; `routine.trigger` fires specs whose HH:MM matches now; `list_routines`, `add_routine`, `remove_routine` abilities; default sleep routine created on persona creation
- Secretary channel: authority="secretary"; used by heartbeat nudges; exposes calendar, reminder, schedule, remind, reach_out, manifest_destiny; disables say; `reach_out` ability finds all active channels via `gateways.all_channels()` and sends
- Spec 13: Persona Start (open all channel gateways)
- Spec 14: Persona Stop (close all channel gateways)
- Spec 15: Find Persona (by ID)
- Service entry point (`service.py`) — starts web server; starts gateways; 60-second heartbeat loop
- Web layer (`web/`) — FastAPI + Jinja2/Tailwind; OpenAI-compatible API; dashboard with live WebSocket feed; persona oversight; chat UI
- CLI (`cli/`) — `eternego` command: daemon, service, env, pair subcommands
- Install scripts (`install.sh`, `install.ps1`) — one-command setup, registers system service

### Not started:
- Circuit breaker for continuous tool failures

## Code Style

- Naming: gerund intents ("saying", "doing", "consulting", "reasoning")
- Memory access: always through `memories.agent(persona)` — per-persona, no global memory
- Struggles: disk-based via `struggles.identified_by()` / `struggles.identify()`, not in short-term memory
- All feedback (delivery confirmation, tool results) goes through `memories.agent(persona).remember()`
- Destiny entries: stored as files in `destiny/` dir; `paths.save_destiny_entry()` to write, `paths.read_files_matching()` to read
- History writes: `archive` ability (sleep/reflective) or `manifest_destiny` ability (heartbeat/secretary); `paths.add_history_entry(persona_id, event, content)` for system writes
- Model naming: `models.generate(base_model, persona_id)` — used in create, migrate, sleep
- Signals: plan at start, event at end, every business function
- Exceptions: domain-specific, defined in `exceptions.py`, caught at business layer
- Nudge vs hear: `hear` is for person-facing messages (public thread); `nudge` is for internal system messages (private thread, secretary channel)
