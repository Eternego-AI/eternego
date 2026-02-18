# Eternego — Implementation Document

## Overview

This document defines the technical implementation layer for Eternego — The Eternal I. It translates each business specification into a concrete solution with step-by-step logic, and identifies the reusable platform modules required as infrastructure.

Eternego creates a portable, accumulative AI persona that lives on the person's hardware, learns from every interaction, and is never locked into any vendor. The persona's knowledge is stored as human-readable files that can be applied to any model, upgraded when better models emerge, and never lost.

### Technology Stack

- **Language:** Python
- **Local Models:** Ollama
- **Storage:** Flat files
- **Communication:** Telegram (MVP)
- **Frontier Models:** Anthropic (Claude), OpenAI
- **Fine-tuning:** LoRA
- **Versioning:** Git

---

## Persona File Structure

Each persona is stored under a UUID-based directory. The following files define a persona:

| File | Purpose | Used In Prompt | Trainable | Cleared After Sleep |
|------|---------|---------------|-----------|-------------------|
| `person-identity.md` | Facts about the person (name, birthday, marital status, address, etc.) | No (reference/proof) | No | No |
| `person-traits.md` | Behavioral preferences (prefers DDD, likes GitLab, etc.) | No (source for DNA synthesis) | Yes | Yes |
| `dna.md` | Compressed synthesis of persona knowledge about the person | No (source for training) | Yes (via training) | No |
| `persona-identity.md` | Persona metadata (name, birthday, model, host, etc.) | No (technical reference) | No | No |
| `persona-context.md` | Everything the persona needs in prompt, from persona's perspective | Yes (always in prompt) | No | No |
| `instructions/` | Operating instructions split by concern (principles, permissions, skills, escalation) | Yes (joined and injected as system message) | No | No |
| `skills/` | Directory of skill documents (markdown files) | Yes (loaded into context) | No (but observation is) | No |
| `history/` | Long-term conversation history | Yes (recent context) | No | No |
| `training/` | Raw training pairs in neutral format | No | Used by LoRA | No (accumulates) |
| `config.json` | UUID, name, channel type, credentials, model, frontier provider + key, paths | No | No | No |

### Identity vs. Traits vs. Context

- **person-identity.md** — Source of truth facts. "John Smith, born 1983, married, 2 children." Saved for reference but not directly used in prompts.
- **person-traits.md** — Behavioral preferences that can be trained into the model. "Prefers DDD, direct communication style." Cleared after sleep because the model now embodies these traits.
- **persona-context.md** — The persona's working knowledge, written from its perspective. "I am male, I am a developer, my wife's name is Jane." Always in the prompt because facts cannot be trained into a model.
- **Skills** — Knowledge and procedural documents. Adding a skill also generates an observation in person-traits.md (e.g., "I know DDD") which gets trained into the model, giving it the instinct to use the skill.

### Instructions Architecture

Instructions are split into separate files under `instructions/`, each handling a distinct concern:

| File | Content |
|------|---------|
| `principles.md` | Core operating principles — unique persona, honesty, person has final say |
| `permissions.md` | Permission model — allow, allow permanently, disallow |
| `skills.md` | How to read and follow skill documents |
| `escalation.md` | When and how to escalate (only present when frontier model exists) |

The agent reads and joins all instruction files when building messages. This split allows adding or removing capabilities without touching other instructions.

### Learning Lifecycle

1. Person interacts with persona → thoughts accumulate in short-term memory (RAM).
2. Memory flushed to `history/` (long-term, on disk) after inactivity.
3. Sleep triggers → history digested → observations extracted.
4. Observations split: facts → person-identity.md, traits → person-traits.md, persona perspective → persona-context.md.
5. DNA synthesized from previous DNA + current traits + context. Recurring patterns are bolded.
6. Raw training data generated from DNA (by frontier or local model).
7. Training data formatted for LoRA (ChatML template).
8. LoRA fine-tuning produces adapter weights.
9. person-traits.md cleared (now baked into model).
10. Short-term memory cleared (RAM).
11. Diary triggered (snapshot saved).
12. Next day: persona is smarter, identity file is fresh for new observations.

### Training Data Philosophy

- **Observations are the onboarding package.** When a new model arrives, observations are used to regenerate training data and re-fine-tune. The model gets the same onboarding as any new employee.
- **Raw training data is stored in neutral format** (no model-specific templates). At training time, a formatter wraps the data in the correct template for the current model. This eliminates compatibility concerns across models.
- **LoRA output is model-specific.** Only reusable for the exact same model. Saved to avoid retraining when restoring on the same model.
- **Iteration wins.** A less capable model extracts simpler observations and gets trained at its own level. Each sleep cycle it improves incrementally. No need for perfection on the first pass.
- **Training time constraint:** Sleep should not exceed 5-6 hours. The main factor is number of training pairs. For a Mac Mini M2 with a 7B model, roughly 1000 pairs is the practical limit per cycle.

---

## Spec 1: Environment Preparation

*It makes it easy to set up and prepare an environment for your persona to grow.*

### Solution

1. Detect OS.
2. Check if git is installed. If not, install it via the OS-specific module.
3. Check if Ollama is installed:
    - Windows: `windows.is_installed('ollama')`
    - Linux: `linux.is_installed('ollama')`
    - macOS: `mac.is_installed('ollama')`
4. If not installed, install via the OS-specific module.
5. If no model specified, query the engine for the default (first pulled model).
6. If no model available at all, fail and ask the person to provide a model name.
7. Check if the model is pulled and responding. If not pulled, pull it.
8. Verify the model responds to a test prompt.

### Platform Modules Used

`OS`, `linux`, `mac`, `windows`, `ollama`

---

## Spec 2: Persona Creation

*It gives birth to your persona with minimum but powerful initial abilities.*

### Solution

1. Receive persona name, model, communication channel, and optionally a frontier model.
2. Verify channel is alive by sending a test message and checking the response.
3. Generate a UUID for the persona via `agent.initialize`.
4. Copy the base model into a persona-owned model via `agent.embody`. The new model is named `{base_model}-{persona_id}-{datetime}`. The base model name is stored in `persona.base_model`.
5. Build the agent via `agent.build`: `persona-identity.md`, `persona-context.md`, `training/`.
6. Create empty DNA file via `dna.make`.
7. Start history via `history.start`: create the `history/` directory.
8. Give instructions via `instructions.give`: `principles.md`, `permissions.md`, `skills.md`.
9. Equip basic skills via `skills.equip`: prepare the `skills/` directory.
10. Bond the person to the persona via `person.bond`: `person-identity.md`, `person-traits.md`.
11. If frontier model provided, write `escalation.md` instruction via `instructions.add` — tells the agent to wrap escalation reasons in `<escalate>` tags.
12. Save persona configuration as `config.json`.
13. Ask the local model to generate a 24-word recovery phrase.
14. Save encryption key (derived from phrase) to OS secure storage.
15. Initialize diary directory with git.
16. Encrypt persona data and write the initial diary entry.

### Platform Modules Used

`OS`, `linux`, `mac`, `windows`, `telegram`, `ollama`, `filesystem`, `crypto`, `git`

---

## Spec 3: Persona Migration

*It enables you to migrate your persona so nothing is ever lost.*

### Solution

1. Receive encrypted diary file path and 24-word recovery phrase.
2. Verify environment is ready (Ollama installed, model running). If not, fail.
3. Derive encryption key from the phrase.
4. Decrypt the diary file and unzip the archive.
5. Restore persona directory with original UUID and all files via `agent.distill`. The `base_model` field is read from config with fallback to the current model name for old configs.
6. Copy the base model into a persona-owned model via `agent.embody`.
7. Save persona configuration.
8. Read DNA via `dna.read` and extract observations via `local_model.study` to populate traits and context. If DNA is missing, migration fails with `DNAError`.
9. Save encryption key to OS secure storage.
10. Initialize diary directory and write a new diary entry.
11. Verify all communication channels. Report what works and what doesn't.

### Platform Modules Used

`OS`, `linux`, `mac`, `windows`, `ollama`, `filesystem`, `crypto`, `git`, `telegram`

---

## Spec 4: Persona Feeding

*It lets you feed your persona with your existing AI history so it can know you faster.*

### Solution

1. Receive external data and source type (OpenAI, Anthropic/Claude).
2. Parse the data using the appropriate platform module into role-based text:
    - Claude exports: `anthropic.role_based_text(data)` — extracts from `chat_messages` array.
    - OpenAI exports: `openai.role_based_text(data)` — extracts from `mapping` structure.
3. Send parsed conversations to the local model with the extraction prompt.
4. Model analyzes and returns structured observations (facts, traits, context).
5. Grow the persona with extracted observations:
    - Facts → `person-identity.md`
    - Traits → `person-traits.md`
    - Context → `persona-context.md`

### Notes

- Feeding is immediately effective: observations saved to persona-context.md are available in the very next conversation.
- Deep learning happens after sleep: raw train data gets fine-tuned into the model during the next sleep cycle.

### Platform Modules Used

`openai`, `anthropic`, `ollama`, `filesystem`

---

## Spec 5: Persona Oversight

*It lets you look into your persona's mind — what it knows, what it learned, and how it sees you.*

### Solution

1. Read person identity (`person-identity.md`) and person traits (`person-traits.md`).
2. Read agent identity (`persona-identity.md`) and context (`persona-context.md`).
3. Read skill names from the `skills/` directory.
4. Read conversation names from the `history/` directory.
5. Assign trackable IDs to each entry using a prefix and content hash:
    - `pi-*` for person identity
    - `pt-*` for person traits
    - `pai-*` for persona identity
    - `pc-*` for persona context
    - `sk-*` for skills
    - `hist-*` for history
6. Return everything organized by category.

### Trackable ID Format

Each entry gets an ID composed of a source prefix and a short hash of the content (e.g., `pt-a3f8b2`). This ensures:
- IDs don't change when other entries are deleted.
- If content was already deleted or modified, the hash won't match.
- No re-indexing needed.
- Works even if a UI page was open for days.

### Platform Modules Used

`filesystem`, `crypto`

---

## Spec 6: Persona Control

*It gives you full control over what your persona knows — you always have the final say.*

### Solution

1. Receive one or more trackable entry IDs.
2. Parse each ID into prefix and hash.
3. Route to the appropriate deletion function based on prefix:
    - `pi` → delete from person identity
    - `pt` → delete from person traits
    - `pai` → delete from persona identity
    - `pc` → delete from persona context
    - `sk` → delete skill file
    - `hist` → delete history file
4. If hash doesn't match any existing entry, report error (entry modified or already deleted).

### Notes

- Primary use case: the person curates memory before sleep, removing anything they don't want baked into the model.

### Platform Modules Used

`filesystem`, `crypto`

---

## Spec 7: Persona Interaction

*It gives the persona the ability to sense, think, communicate, act, escalate, and reflect — like a mind.*

The interaction system follows a cognitive architecture with two loops:

- **Reactive**: sense → reason → route thoughts → reflect
- **Proactive**: predict → reason → act (draft, not yet implemented)

### Cognitive Model

The agent thinks by streaming tokens from the local model. Each token is accumulated and analyzed for intent using XML-like tags:

- `<think>...</think>` — internal reasoning, not shown to the person
- `<escalate>...</escalate>` — escalation request, content is sent to frontier
- Tool calls in the response — action execution
- Plain text — communication to the person

Each unit of output is a `Thought` with an `intent`:

| Intent | Meaning | Spec |
|---|---|---|
| `"saying"` | Text to communicate to the person | say |
| `"doing"` | Tool call to execute | act |
| `"consulting"` | Needs a more powerful model | escalate |
| `"reasoning"` | Internal thinking | shared as context only |

### The Thinking Pattern

Both agent and frontier produce thoughts through the same `Thinking` class. This is a reusable wrapper around any reasoning function:

```python
# Agent thinking — uses local model
think = agent.given(persona, stimulus)
async for thought in think.reason():
    # route by thought.intent

# Frontier thinking — uses external API
async for thought in frontier.consulting(model, prompt).reason():
    # route by thought.intent
```

### Memory

Short-term memory is an in-memory document store (`Memory` class). The agent accumulates documents as the conversation progresses:

| Document Type | When Created | Contents |
|---|---|---|
| `stimulus` | Person sends a message | role, content, channel |
| `say` | Agent produces text | content |
| `act` | Agent executes a tool | tool_calls, result |
| `observation` | After escalation completes | list of messages from frontier interaction |
| `communicated` | Channel confirms delivery | channel, content |

The agent builds its message history from memory on each reasoning cycle. This means the agent has full conversational context without file I/O.

### Spec 7a: Sense

*It lets the persona sense a stimulus from a channel and process it.*

1. Receive prompt and channel from person.
2. Give the stimulus to the agent: `agent.given(persona, {type: "stimulus", role: "user", content: prompt, channel: channel.name})`.
3. Iterate the thinking process: `think.reason()`.
4. For each thought:
    - `"saying"` → call `say(persona, thought, channel)`
    - `"doing"` → call `act(persona, thought)`
    - `"consulting"` → call `escalate(persona, thought.content, channel)`
    - `"reasoning"` → share via bus
5. After all thoughts processed, call `reflect(persona)`.
6. Return outcome.

### Spec 7b: Say

*It lets the persona express a thought through a channel.*

1. Determine target channels: the specific channel if provided, otherwise all persona channels.
2. If no channels available, broadcast failure and return.
3. For each channel, send the message via `channels.send(channel, thought.content)`.
4. Record delivery in memory via `memories.agent(persona).remember({type: "communicated", channel, content})`.
5. Broadcast success per channel.

### Spec 7c: Act

*It lets the persona act on the world by executing a tool call.*

1. Ask the person for permission via `bus.ask("Can I run this command?", {tool_calls})`.
2. Check returned signals for a `"Run command authorized"` message matching the tool calls.
3. If not authorized: note rejection in persona memory via `memories.agent(persona).remember({...})`, return failure.
4. If authorized: execute the tool calls via `system.execute(thought.tool_calls)`.
5. Note the result in persona memory: `memories.agent(persona).remember({type: "act", tool_calls, result})`.
6. The agent's reasoning loop sees the result and continues (loop inside `agent.reason`).

The while loop inside `agent.reason` keeps the agent thinking as long as it is acting. When no action is taken in a cycle, the loop breaks naturally.

In the `sense` spec, if a tool call fails, all subsequent tool calls in the same interaction are skipped to prevent cascading failures.

### Spec 7d: Escalate

*It lets the persona escalate to a frontier model when the task exceeds its ability.*

1. The local model wraps its escalation reason in `<escalate>` tags.
2. `agent.reason()` yields `Thought(intent="consulting", content=reason)`.
3. `sense` routes to `escalate(persona, prompt, channel)`.
4. Build observation list starting with the user prompt.
5. Call `frontier.consulting(persona, prompt).reason()`.
6. For each frontier thought:
    - `"saying"` → append to observation, call `say`
    - `"doing"` → append to observation, call `act`
    - `"reasoning"` → **not observed**, shared via bus only
7. After completion, `memories.agent(persona).remember({"type": "observation", "observation": observation})` stores the interaction for later learning.

The frontier module checks `model.provider` and routes to the appropriate platform module:
- `"anthropic"` → `anthropic.stream(api_key, model, messages)`
- `"openai"` → `openai.stream(api_key, model, messages)`

Both platform modules normalize output to `{"message": {"content": ..., "tool_calls": ...}, "done": bool}`.

### Spec 7e: Reflect

*It lets the persona reflect on what it learned from the interaction.*

1. Give the agent a reflection prompt via `agent.given(persona, prompts.reflection())`.
2. Iterate the thinking process.
3. Route saying thoughts through `say`.
4. Route reasoning thoughts through `bus.share`.

Called automatically at the end of every `sense` cycle.

### Spec 7f: Predict

*It lets the persona anticipate and act without external stimulus.*

1. Give the agent a prediction prompt via `agent.given(persona, prompts.prediction())`.
2. Iterate the thinking process.
3. Route saying thoughts through `say`.
4. Route reasoning thoughts through `bus.share`.

### Platform Modules Used

`ollama`, `anthropic`, `openai`, `telegram`, `linux`, `mac`, `windows`, `filesystem`

---

## Spec 8: Persona Equipment

*It lets you equip your persona with new skills so it can do more for you.*

### Solution

1. Receive a skill document (markdown file).
2. Save to persona's `skills/` directory.
3. Generate an observation (e.g., "I know DDD") and add to person-traits.md.

### Notes

- Skills are immediately available in the persona's context for the next conversation.
- The observation gets trained into the model on the next sleep cycle.
- A skill can be knowledge ("DDD principles"), procedural ("steps to deploy to AWS"), or API-specific ("how to call the calendar API").

### Platform Modules Used

`filesystem`

---

## Spec 9: Persona Diary

*It preserves your persona's life so it survives across time, hardware, and changes.*

### Solution

1. Retrieve the encryption phrase from OS secure storage.
2. Zip all persona files into a single archive.
3. Encrypt the archive using the key derived from the phrase.
4. Save the encrypted file to the diary directory.
5. Git commit with a diary entry message.

### Diary Contents

Everything needed to restore the persona:
- person-identity.md, person-traits.md
- persona-identity.md, persona-context.md
- dna.md
- Instructions directory
- Skills directory
- Raw training data
- Configuration (model, channels, frontier)

### Notes

- The diary is encrypted with the key derived from the person's 24-word recovery phrase.
- Git provides versioning, history, and rollback for free. Each sleep cycle is a commit.
- API keys and channel tokens are included because the diary is encrypted.

### Platform Modules Used

`filesystem`, `crypto`, `git`

---

## Spec 10: Persona Sleep

*It lets your persona rest, reflect, and grow stronger from everything it experienced.*

### Solution

1. Recall conversation history from disk (`history.recall`).
2. If there is history, extract observations via `local_model.observe` and grow the persona (facts, traits, context saved to files).
3. Synthesize new DNA: `dna.assemble_synthesis` reads previous DNA + current traits + context, frontier or local model produces the synthesis, `dna.evolve` writes the result.
4. Read DNA via `agent.sleep`, send to the model (or frontier if available) to generate training data.
5. Save training data to `training/` directory.
6. Generate a new model name via `models.generate_name`.
7. Fine-tune the base model using LoRA. The new model gets the generated name.
8. Verify the fine-tuned model responds correctly.
9. Delete the old persona model. Failure is non-breaking (logged but does not stop sleep).
10. Wake up: save the new model name, clear person-traits.md (baked into model), clear short-term memory.
11. Trigger Persona Diary (Spec 9).

### Fine-tuning Details

- **LoRA (Low-Rank Adaptation)** adds a small layer of parameters on top of the base model. Only this layer is trained, making it feasible on consumer hardware.
- The base model stays untouched. The LoRA adapter is a small file (megabytes, not gigabytes).
- Training data is formatted using ChatML template by `lora.format()` before training.
- Training time is primarily driven by: number of training pairs > model size > number of epochs.
- Target: sleep should not exceed 5-6 hours, matching natural human sleep patterns.
- During sleep, the persona is unavailable (the model is being retrained).

### Platform Modules Used

`ollama`, `anthropic`, `openai`, `lora`, `filesystem`

---

## Spec 13: Persona Start

*It opens all channels for a persona and starts listening for messages.*

### Solution

1. Verify the persona has channels configured.
2. For each channel, create an `on_message` closure that calls `sense`.
3. Call `channels.listen` which creates a `Gateway` object and starts a polling thread.
4. Register the gateway via `gateways.of(persona).add(gateway)`.
5. If the channel type is unsupported, `channels.listen` raises `ChannelError`.

### Threading Model

Each channel runs in its own daemon thread. The thread polls the platform API (e.g., Telegram `getUpdates`). When a message arrives, it bridges back to the main event loop via `asyncio.run_coroutine_threadsafe`, which schedules `on_message` (and thus `sense`) on the main thread. All signals, logging, and business logic run on the main event loop.

For group chats (Telegram), the poll only triggers `on_message` when the persona's username is mentioned.

### Platform Modules Used

`telegram`

---

## Spec 14: Persona Stop

*It closes all channels for a persona.*

### Solution

1. Call `gateways.of(persona).close_all()`.
2. Each gateway's `close()` sets a threading Event flag.
3. The polling thread checks `is_stopped` on each loop iteration and exits.
4. If no active gateways exist, return failure.

### Platform Modules Used

None (gateway lifecycle is managed in core).

---

## Spec 15: Find Persona

*It finds a persona by its unique ID so other systems can locate and interact with it.*

### Solution

1. Receive a persona ID.
2. Call `agent.find(persona_id)` which loads the config from `~/.eternego/personas/{id}/config.json`.
3. Return the persona wrapped in an `Outcome`.

### Notes

- Used by the web API to resolve the `model` field in OpenAI-compatible requests to a `Persona` object.
- Fails with a user-friendly message if the persona ID does not exist on disk.

### Platform Modules Used

`filesystem`

---

## Service Entry Point

`service.py` is the application entry point, designed to run as a system service (systemd on Linux, launchd on macOS, Task Scheduler on Windows). Installed via `install.sh` (Linux/macOS) or `install.ps1` (Windows). The `eternego` CLI command (installed via `pip install -e .`) starts the daemon with `eternego daemon`.

1. Parse flags: `-v` (verbosity), `--predict-interval` (default 60s, 0 to disable), `--port` (default 5001), `--host` (default 127.0.0.1).
2. Set up the default logger to write to `eternego.log`.
3. Subscribe signal handlers: `log_signal` (prints and writes to log file) for all Events and Plans, `restart_gateway` for Commands.
4. Load all personas via `persona.agents()`.
5. For each persona, call `persona.start()`.
6. If `--predict-interval > 0`, start the predict loop as a background asyncio task — calls `persona.predict(persona, channel)` for each persona every N seconds.
7. Start the FastAPI web server as a background asyncio task via uvicorn on `--host:--port`.
8. Keep the event loop alive for signal handling and `on_message` callbacks from threads.

The restart handler responds to `"Restart gateway"` commands by stopping then starting the persona's gateway, with outcome checks at each step.

---

## Web Layer

The web layer (`web/`) sits outside `application/` alongside `service.py`. It is started by the service on startup and provides two interfaces:

### OpenAI-Compatible API

Personas are exposed as models. Any OpenAI-compatible client pointed at `http://localhost:5001` can list and chat with personas.

| Endpoint | Business Call | Description |
|---|---|---|
| `GET /v1/models` | `persona.agents()` | List all personas as model objects (`id` = persona ID) |
| `GET /v1/models/{id}` | `persona.find(id)` | Retrieve a single persona as a model object |
| `POST /v1/chat/completions` | `persona.find(model)` → `persona.chat()` | Chat with a persona; `model` field is the persona ID |

The `model` field in all responses contains the persona ID. Clients use `GET /v1/models` to discover available persona IDs, then pass the ID as `model` in chat requests.

### Dashboard

`GET /dashboard` renders an HTML page listing all personas with their name, ID, and local model. Served at `http://localhost:5001/dashboard`.

### Internal API

`GET /api/*` — reserved for internal Eternego endpoints (persona creation, migration, etc.). Currently a placeholder, routes will be added as the TUI and management layer are built.

### Structure

```
web/
├── app.py          # FastAPI app, mounts all routers
├── requests.py     # Pydantic request validation models
└── routes/
    ├── openai.py   # /v1/* endpoints
    ├── pages.py    # /dashboard
    └── api.py      # /api/* (internal)
```

Routes call `application/business/` only — same rule as `service.py`.

---

## Platform Modules

The platform layer consists of reusable modules that can be shared across projects. Each module has a single, clear responsibility.

| Module | Responsibility |
|--------|---------------|
| `OS` | Detect operating system |
| `linux` | Linux-specific shell operations and secure storage |
| `mac` | macOS-specific shell operations and secure storage (Keychain) |
| `windows` | Windows-specific shell operations and secure storage (Credential Manager) |
| `telegram` | Telegram Bot API communication (send, poll, is_mentioned) |
| `ollama` | All local model communication: serve, pull, generate, stream, copy, delete, model management |
| `anthropic` | Anthropic Claude API streaming and export parsing |
| `openai` | OpenAI API streaming and export parsing |
| `crypto` | Key derivation, encryption/decryption, content hashing |
| `filesystem` | Directory creation, file read/write, zip/unzip |
| `git` | Git repository operations (init, add, commit) |
| `datetimes` | Date/time operations |
| `logger` | Structured logging |
| `observer` | Pub/sub signal system (Plan, Event, Message, Inquiry, Command) |
| `lora` | LoRA fine-tuning and training data formatting (lazy imports) |


