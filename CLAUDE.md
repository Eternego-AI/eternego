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

Business imports core. Core imports platform. Never upward. Presentation (`telegram/` for MVP) sits outside `application/` and only calls business.

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
  thought.intent == "saying"     → say spec → bus.order("Say") → channel delivers
  thought.intent == "doing"      → act spec → system.execute → agent.note(result)
  thought.intent == "consulting"  → escalate spec → frontier.consulting → agent.observe
  thought.intent == "reasoning"   → bus.share (internal, not shown to person)
```

### Key classes (application/core/data.py)

- `Thought(intent, content, tool_calls)` — single unit of reasoning output
- `Thinking(reason_by)` — wraps any async generator, exposes `.reason()`
- `Memory` — short-term in-memory document store, accessed via `agent.memory()`

### Fluent API

```python
# Local model thinking
think = agent.given(persona, {"type": "stimulus", "role": "user", "content": prompt})
async for thought in think.reason():
    ...

# Frontier model thinking — same pattern
async for thought in frontier.consulting(model, prompt).reason():
    ...
```

### Tag detection in agent.reason()

- `<think>...</think>` → reasoning intent
- `<escalate>...</escalate>` → consulting intent
- Tool calls → doing intent
- Plain text → saying intent

### Memory vs History

- **Memory** — short-term, in-process (`Memory` class). Holds documents from the current session. Accessed via `agent.memory()`. Cleared on wake up.
- **History** — long-term, on disk (`history/` directory). Persists across sessions. Used for oversight, control, and sleep observation extraction.

### Memory document types

| Type | Created by | Contains |
|---|---|---|
| `stimulus` | `agent.given()` | role, content, channel |
| `say` | `agent.reason()` internally | content |
| `act` | `agent.note()` | tool_calls, result |
| `observation` | `agent.observe()` | frontier conversation (minus reasoning) |
| `communicated` | `agent.note()` | channel, content |

### Action loop

Inside `agent.py`'s `_reason()` closure (the function wrapped by `Thinking`), a `while True` loop rebuilds messages from memory and re-streams from the local model after each tool execution. When a cycle produces no tool calls, the loop breaks. This means the agent can chain tool calls naturally — think, act, see result, think again — without the business layer needing to re-call `sense`.

### Escalation

Local model wraps in `<escalate>` tags → frontier streams via anthropic/openai platform modules → thoughts routed through same say/act specs → frontier reasoning is NOT observed (agent develops its own reasoning path).

## Module Map

### Business (application/business/)

| Module | Functions |
|---|---|
| `environment.py` | prepare, check_model |
| `persona.py` | create, migrate, feed, grow, equip, sense, say, act, escalate, reflect, predict, oversee, control, write_diary, sleep |
| `gateway.py` | verify_channel |
| `outcome.py` | Outcome dataclass |

### Core (application/core/)

| Module | Role |
|---|---|
| `agent.py` | Memory accessor, given(), note(), observe(), instructions(), initialize, embody(), save, identity CRUD, shelve_skill(), summarize_skill(), recall(), sleep(), save_training_set(), wake_up() |
| `person.py` | Person facts/traits CRUD |
| `frontier.py` | allow_escalation(), consulting() → returns Thinking, respond() |
| `local_model.py` | stream() async generator, digest(), assess_skill(), generate_encryption_phrase(), respond() |
| `models.py` | generate_name() |
| `local_inference_engine.py` | is_installed(), install(), pull(), check(), get_default_model(), copy(), delete(), fine_tune() |
| `bus.py` | Signal dispatch: propose, broadcast, share, ask, order |
| `system.py` | execute(), is_installed(), install(), save/get_phrases(), make_rows_traceable() |
| `data.py` | Channel, Model, Thought, Thinking, Memory, Observation, Persona |
| `prompts.py` | BASIC_INSTRUCTIONS, ESCALATION, EXTRACTION, SKILL_ASSESSMENT, RECOVERY_PHRASE, SLEEP |
| `exceptions.py` | All domain exceptions |
| `diary.py` | open_for(), open(), record() |
| `external_llms.py` | read() — parses OpenAI/Anthropic exports |
| `channel.py` | send(), assert_receives() |

### Platform (application/platform/)

| Module | Wraps |
|---|---|
| `ollama.py` | Ollama HTTP API (get, post, delete, stream_post) |
| `anthropic.py` | Anthropic Messages API streaming + export parsing |
| `openai.py` | OpenAI Chat API streaming + export parsing |
| `telegram.py` | Telegram Bot API |
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
- Spec 7a: Sense (reactive loop)
- Spec 7b: Say (channel communication with confirmation)
- Spec 7c: Act (tool execution with permission check via bus.ask)
- Spec 7d: Escalate (frontier routing with observation)
- Spec 7e: Reflect (reflection prompt after each sense cycle)
- Spec 7f: Predict (prediction prompt for proactive behavior)
- Spec 8: Persona Equipment (shelve, summarize, grow)
- Spec 9: Persona Diary
- Spec 10: Persona Sleep (recall history, digest observations, generate training, LoRA fine-tuning, wake up)

### Not started:
- History lifecycle (short-term memory flush to history/)
- Circuit breaker for continuous tool failures

## What to Work On Next

1. **History lifecycle** — flush short-term memory to `history/` after inactivity.

2. **Channel implementation** — Telegram presentation layer.

## Code Style

- Naming: gerund intents ("saying", "doing", "consulting", "reasoning")
- Memory access: always through `agent.memory()`, never `_memory` directly
- All feedback goes through `agent.note()` — delivery confirmation, tool results
- Frontier learning: `agent.observe()` stores conversation minus reasoning
- Disk-based history listing: `agent.history(persona)` (long-term, on disk)
- Model naming: `models.generate_name(base_model, persona_id)` — used in create, migrate, sleep
- Instructions: split files under `instructions/` dir, joined by `agent.instructions(persona)`
- Signals: plan at start, event at end, every business function
- Exceptions: domain-specific, defined in `exceptions.py`, caught at business layer
