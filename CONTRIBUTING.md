# Contributing to Eternego

This document covers the architecture, conventions, and cognitive system you need to understand before making changes.

---

## Layers

The application has three layers inside `application/`:

```
business/    WHY — What should happen, reads like the README
core/        HOW — Where we engineer the solutions
platform/    WHAT — What external tools actually provide, nothing more
```

Dependencies flow downward only: business imports core, core imports platform. Never upward.

The service entry point (`service.py`), the heartbeat (`heart.py`), the web layer (`web/`), and the CLI (`cli/`) sit outside `application/`. They call business functions only and never touch core or platform directly.

---

## Process

We always work top-down:

1. **Write the business spec first.** Define what the feature does as a clear spec, then translate it into a business function. The function should be self-documenting — a business person can read it and understand what happens. Add `bus.propose` at the start, `bus.broadcast` at the end, and calls to core functions in between.

2. **Add core signatures only for what business asked for.** If the business spec calls `local_inference_engine.check(model)`, add `check(model)` to the core module. Never add core functions speculatively.

3. **Implement core functions.** This is where we solve problems — what steps are needed, what platform capabilities to use, how to combine them. Core functions start with a log and use platform modules for all infrastructure.

4. **Add platform functions only for what the tool provides.** If Ollama has `GET /api/tags`, the platform module has `get()`. If Ollama does not have a "get default model" concept, the platform module does not have `get_default_model()` — that logic lives in core.

---

## Business Layer

Every business function is `async`, returns `Outcome[T]`, starts with `bus.propose`, and ends with `bus.broadcast`. It catches domain exceptions from core and returns user-friendly messages. It never contains engineering logic.

### Signals

Every business function sends at least two signals through the bus:

| Method | Signal Type | Purpose |
|---|---|---|
| `bus.propose` | Plan | Announce intent before action |
| `bus.broadcast` | Event | Announce result after action |
| `bus.share` | Message | Share information passively |
| `bus.ask` | Inquiry | Request input from subscribers |
| `bus.order` | Command | Command an action, expect signals back |

### Error Handling

Error handling flows upward in three steps:

1. **Platform** raises raw errors (`URLError`, `OSError`, etc.)
2. **Core** catches platform errors and raises domain exceptions (`InstallationError`, `EngineConnectionError`, etc.)
3. **Business** catches domain exceptions and returns user-friendly `Outcome` with a broadcast event

Do not add try/catch to business specs before implementing core. Go down first — implement core, see what platform errors it faces, define domain exceptions, add catches in core. Then come back up and add catches in business.

---

## Core Layer

Core functions exist because a business spec calls them. Every core function starts with a log, uses platform modules for all infrastructure, never sends signals, and never returns `Outcome` — it returns data or raises exceptions.

---

## Platform Layer

Platform modules expose what external tools actually offer — nothing invented, nothing wrapped beyond what the tool gives. They are portable across projects and contain no project-specific logic.

---

## The Cognitive System

This is the persona's brain. Understanding it is essential for most contributions.

### Data Model

Four types form a cognitive graph:

```
Signal → Perception → Thought
                        ↓
                      Meaning
```

- **Signal** — an atomic message (user, assistant, or system) with a timestamp
- **Perception** — a group of related signals forming a conversation thread, identified by an *impression* (a short description of what this thread is about)
- **Meaning** — a Python class that defines how to handle a type of interaction (e.g., Reminder, Shell, Chatting)
- **Thought** — a perception paired with a meaning — the cognitive work unit that flows through the pipeline

### The Pipeline

The mind runs a continuous loop through five stages:

```
understand → recognize → answer → decide → conclude
```

Each stage has a clear entry condition. A thought can only be in one stage at a time:

| Stage | Entry Condition | What Happens | Exits By |
|-------|----------------|--------------|----------|
| **understand** | Unattended user signal | Route signal to a perception thread | Attaching signal to perception |
| **recognize** | Perception with no thought | Match perception to a meaning, creating a thought | Creating a thought |
| **answer** | Thought unprocessed, last signal is user, meaning has reply/clarify | Generate a response to the person | Appending assistant signal |
| **decide** | Thought unprocessed, meaning has path, answer is done | Extract structured data, execute action | Resolving thought (or retrying on error) |
| **conclude** | Thought processed but not concluded | Confirm result to the person | Setting concluded_at |

After each stage, the clock checks if new signals arrived. If so, it restarts the pipeline from understand. This ensures the persona is always responsive.

### Meaning Methods

Each method on a Meaning maps to a pipeline stage:

**`name`** (class attribute) — identifies the meaning in the recognition list.

**`description() → str`** — one sentence defining what interactions this covers. Used by the recognize stage to match a perception to this meaning.

**`reply() → str | None`** — prompt for the answer stage. How to respond on first contact. This runs BEFORE any action is taken.

Important: The reply output is appended to the conversation thread and becomes visible to the decide stage. Never ask the model to state specific extracted values (times, dates, names) — if it gets them wrong, the error propagates into extraction.

**`clarify() → str | None`** — prompt for retry after an error. Only runs when the conversation already contains an error message from a failed action.

**`path() → str | None`** — prompt for the decide stage. Tells the model what structured data to extract and what JSON schema to return. For tool-using meanings, reference tools by their exact name. Return None for conversational-only meanings.

Important: Tell the model to extract from what the person said, not from assistant messages in the thread.

**`summarize() → str | None`** — prompt for the conclude stage. The final message confirming what was done. Return None to skip.

**`run(persona_response: dict)`** — executes the action. The default dispatches tool calls from the JSON that path() produced. Override only for custom logic (e.g., file I/O). Return None on success (pipeline moves to conclude), return a Signal on error (pipeline retries via clarify).

### Adding a New Meaning

Create a file in `application/core/brain/mind/meanings/`:

```python
from application.core.brain.data import Meaning


class WeatherForecast(Meaning):
    name = "Weather Forecast"

    def description(self):
        return "The person wants to know the weather for a location and time."

    def clarify(self):
        return (
            "The weather lookup failed. Look at the error, explain what "
            "went wrong, and ask the person to clarify the location or date."
        )

    def reply(self):
        return "Acknowledge briefly that you will check the weather."

    def summarize(self):
        return "Share the forecast naturally — temperature, conditions, and anything notable."

    def path(self):
        return (
            "Extract the weather request from what the person said (ignore assistant messages).\n"
            'Return JSON: {"tool": "linux.execute_on_sub_process", "command": "curl ..."}\n'
        )
```

Then register it in `meanings/__init__.py` by importing it and adding it to the `built_in()` list.

### Escalation — Learning New Meanings at Runtime

When no existing meaning matches a perception, the recognize stage selects Escalation. This triggers `ego.escalate()`, which asks a frontier model (or falls back to the local model) to generate a new Meaning class as Python code.

The generated code is saved to `~/.eternego/personas/<id>/home/meanings/` and loaded dynamically. The new meaning is used immediately for the current interaction and persists across restarts.

The escalation prompt teaches the frontier model how the pipeline works, what each method does, and the pitfalls to avoid (like error propagation from reply to decide). This is intentional — a well-informed frontier model produces meanings that work correctly with a weaker local model.

### The Sleep Cycle

When a persona sleeps (triggered manually or by a daily routine):

1. The mind finishes processing all active thoughts
2. **learn_from_experience** — conversations are analyzed to extract and update:
   - `person.md` — facts about the user (timezone, relationships, preferences)
   - `traits.md` — behavioral patterns the persona observes
   - `wishes.md` — goals and aspirations
   - `struggles.md` — recurring obstacles
   - `context.md` — operational context
   - `dna.md` — synthesized character description
3. All thoughts are archived to `history/`
4. **grow** — training pairs are generated from the DNA and the persona is fine-tuned on local hardware (if GPU is available)
5. Memory is cleared for the next waking cycle

### Persona Data on Disk

Everything lives in `~/.eternego/personas/<id>/home/`:

```
config.json       — persona configuration
person.md         — facts about the user
traits.md         — observed behavioral patterns
wishes.md         — user's goals and aspirations
struggles.md      — recurring obstacles
context.md        — operational context
dna.md            — synthesized character (used for training)
mind/memory.json  — cognitive graph (signals, perceptions, thoughts)
history/          — archived conversations
destiny/          — scheduled reminders and events
notes/            — user's saved notes
meanings/         — learned meaning definitions (Python)
training/         — generated training pairs
```

All files are human-readable and editable. Modifying them directly changes the persona's knowledge.

---

## Code Style

- **Naming**: gerund intents (`saying`, `doing`, `consulting`, `reasoning`)
- **Memory access**: always through `memories.agent(persona)` — per-persona, no global memory
- **Destiny entries**: `paths.save_destiny_entry()` to write, `paths.read_files_matching()` to read
- **History writes**: `paths.add_history_entry(persona_id, event, content)` for system writes
- **Signals**: plan at start, event at end, every business function
- **Exceptions**: domain-specific, defined in `exceptions.py`, caught at business layer
