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
| `person-traits.md` | Behavioral preferences (prefers DDD, likes GitLab, etc.) | No (source for training) | Yes | Yes |
| `persona-identity.md` | Persona metadata (name, birthday, model, host, etc.) | No (technical reference) | No | No |
| `persona-context.md` | Everything the persona needs in prompt, from persona's perspective | Yes (always in prompt) | No | No |
| `foundational-instructions.md` | Operating instructions: how to use tools, escalate, learn, signal actions | Yes (always in prompt) | No | No |
| `skills/` | Directory of skill documents (markdown files) | Yes (loaded into context) | No (but observation is) | No |
| `memory/` | Conversations since last sleep | Yes (recent context) | No | Yes (cleared after sleep) |
| `train-data/` | Raw training pairs in neutral format | No | Used by LoRA | No (accumulates) |
| `lora/` | LoRA adapter output + model metadata | No | Is the output | Replaced each sleep |
| `config.json` | UUID, name, channel type, credentials, model, frontier provider + key, paths | No | No | No |

### Identity vs. Traits vs. Context

- **person-identity.md** — Source of truth facts. "John Smith, born 1983, married, 2 children." Saved for reference but not directly used in prompts.
- **person-traits.md** — Behavioral preferences that can be trained into the model. "Prefers DDD, direct communication style." Cleared after sleep because the model now embodies these traits.
- **persona-context.md** — The persona's working knowledge, written from its perspective. "I am male, I am a developer, my wife's name is Jane." Always in the prompt because facts cannot be trained into a model.
- **Skills** — Knowledge and procedural documents. Adding a skill also generates an observation in person-traits.md (e.g., "I know DDD") which gets trained into the model, giving it the instinct to use the skill.

### Learning Lifecycle

1. Person interacts with persona → conversations accumulate in memory.
2. Sleep triggers → model extracts observations from conversations.
3. Observations split: facts → person-identity.md, traits → person-traits.md, persona perspective → persona-context.md.
4. Raw training data generated from traits (by frontier or local model) in neutral format.
5. Training data formatted for current model's template.
6. LoRA fine-tuning produces adapter weights.
7. person-traits.md cleared (now baked into model).
8. Memory cleared (conversations consumed).
9. Diary triggered (snapshot saved).
10. Next day: persona is smarter, identity file is fresh for new observations.

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
2. Check if Ollama is installed:
    - Windows: `windows.shell('where ollama')`
    - Linux: `linux.shell('which ollama')`
    - macOS: `mac.shell('which ollama')`
3. If already installed, skip to step 6.
4. If not installed:
    - Linux: `linux.shell.pipe(curl.silent_follow('https://ollama.com/install.sh'))`
    - macOS: `mac.shell('brew install ollama')`
    - Windows: Show message "Please install Ollama from ollama.com" and wait for confirmation.
    - Other OS: Show message "Eternego requires Linux, macOS, or Windows" and stop.
5. Verify installation by repeating step 2.
6. Check if Ollama server is running by hitting `localhost:11434`. If not, start it via `ollama serve`.
7. Check available RAM via `os.ram()`, check GPU and VRAM via `os.gpu()`.
8. From a curated model list, filter by hardware specs, select best fit, present pre-filled but editable.
9. Pull the selected model via `ollama pull <model>`.
10. Send a request to `/api/generate` with a simple prompt, verify successful response.

### Platform Modules Used

`os`, `linux`, `mac`, `windows`, `curl`

---

## Spec 2: Persona Creation

*It gives birth to your persona with minimum but powerful initial abilities.*

### Solution

1. Receive persona name, communication channel type, channel credentials (for Telegram: bot token), and optionally frontier provider name + API key.
2. Verify channel is alive:
    - Telegram: send a test message using bot token, verify send and receive works.
3. Generate a UUID for the persona.
4. Save persona name → UUID mapping.
5. Create persona directory under that UUID with subdirectories for identity, memory, config, skills, train-data, and lora.
6. Copy foundational instructions into the persona's directory.
    - 6.a. If frontier API key is provided, test it with a simple request to the appropriate provider module. If valid, add instruction to the persona for when to use the frontier model (low confidence, lack of capability, explicit person request) and how to learn from frontier responses.
7. Save persona configuration (name, UUID, channel type, channel credentials, model name, frontier provider + API key if provided, paths).
8. Send a prompt to the persona's model asking it to generate a 24-word recovery phrase.
9. Show recovery phrase to person, require confirmation they saved it.
10. Derive encryption key from the phrase.
11. Save encryption key to OS secure storage (via the appropriate OS module).
12. Trigger Persona Diary (Spec 10) to save initial state.

### Foundational Instructions Include

- How to signal escalation via structured payload when the persona cannot handle a request.
- How to signal action requests that require command execution.
- Permission model explanation (allow / allow permanently / disallow).
- Command execution capability: the persona can execute shell commands.
- How to learn from frontier model responses.
- How to extract observations from conversations.

### Platform Modules Used

`os`, `linux`, `mac`, `windows`, `telegram`, `ollama`, `uuid`, `filesystem`, `crypto`, `anthropic`, `openai`

---

## Spec 3: Persona Migration

*It enables you to migrate your persona so nothing is ever lost.*

### Solution

1. Receive encrypted diary file path and 24-word recovery phrase.
2. Verify environment is ready (Ollama installed, model running). If not, stop and ask person to run Spec 1 first.
3. Detect the running model name.
4. Derive encryption key from the phrase.
5. Decrypt the diary file.
6. Unzip the archive.
7. Restore persona directory with original UUID and all files.
8. Save encryption key to OS secure storage.
9. Initialize diary directory as git repo with restored data as first commit.
10. Format raw train data for the detected model and run LoRA training.
11. Verify all connections (channel, frontier API). Report what works and what doesn't with instructions to update.

### Platform Modules Used

`os`, `linux`, `mac`, `windows`, `ollama`, `filesystem`, `crypto`, `lora`, `formatter`, `git`, `telegram`, `anthropic`, `openai`

---

## Spec 4: Persona Feeding

*It lets you feed your persona with your existing AI history so it can know you faster.*

### Solution

1. Receive external data and source type (OpenAI, Anthropic, etc.).
2. Parse the data using the appropriate module (openai, anthropic) into a common format.
3. Send to frontier model for analysis if available, otherwise use local model.
4. Extract observations: facts → person-identity.md, preferences/traits → person-traits.md.
5. Transform person data into persona perspective → persona-context.md.
6. Generate raw train data from extracted traits in neutral format.
7. Save raw train data for next sleep cycle.

### Notes

- Feeding is immediately effective: observations saved to persona-context.md are available in the very next conversation (like giving an employee a cheat sheet).
- Deep learning happens after sleep: raw train data gets fine-tuned into the model during the next sleep cycle (like the employee internalizing the knowledge).
- Different export formats are handled by the existing frontier provider modules (openai, anthropic).

### Platform Modules Used

`openai`, `anthropic`, `ollama`, `filesystem`

---

## Spec 5: Persona Oversight

*It lets you see into your persona's mind — what it knows, what it learned, and how it sees you.*

### Solution

1. Load all persona files, skills, and current memory.
2. Assign trackable IDs (source prefix + content hash) to each entry including skills.
3. Return separate objects:
    - Person identity (`pi-*`)
    - Person traits (`pt-*`)
    - Persona identity (`pai-*`)
    - Persona context (`pc-*`)
    - Skills (`sk-*`)
    - Memory (`mem-*`)
4. Return persona age (calculated from persona-identity.md birthday).

### Trackable ID Format

Each entry gets an ID composed of a source prefix and a short hash of the content (e.g., `pt-a3f8b2`). This ensures:

- IDs don't change when other entries are deleted.
- If content was already deleted or modified, the hash won't match — we know the ID is invalid.
- No re-indexing needed.
- Works even if a UI page was open for days.

### Platform Modules Used

`filesystem`

---

## Spec 6: Persona Control

*It gives you full control over what your persona knows — you always have the final say.*

### Solution

1. Receive a trackable ID.
2. Parse prefix to identify source type.
3. Search for matching hash in the corresponding file.
4. If found:
    - If it's a skill (`sk-*`): delete the skill document from skills/ directory AND remove the corresponding observation from person-traits.md (e.g., remove "I know DDD").
    - Otherwise: delete the entry from the corresponding file.
5. If not found, return error: entry no longer exists or has been modified.

### Notes

- Primary use case: the person curates memory before sleep, removing anything they don't want baked into the model.
- Deleting a skill removes both the skill document and the associated trait observation, ensuring the model won't be trained on a removed skill.

### Platform Modules Used

`filesystem`

---

## Spec 7: Persona Interaction

*It will be responsive on any communication channel, communicate through one and continue on others, and act on your behalf using the skills it has.*

*This spec merges the original Persona Interaction (Spec 7) and Persona Action (Spec 9) as the action flow is a natural extension of interaction.*

### Solution

1. Receive message from person through configured channel.
2. Build prompt: foundational instructions + persona-context.md + skills + current memory + message.
3. Send to local model.
4. Parse response. If escalation flag is present → send same context to frontier, get response.
5. If the response includes a command/action to execute:
    - Present the plan to the person.
    - Ask for permission (allow / allow permanently / disallow).
    - If allowed, execute via appropriate OS shell module.
    - Return execution result to the model to form final response.
6. Save conversation (message + response) to memory.
7. Send response back through the same channel.

### Escalation

The persona self-assesses its ability to handle each request. When it cannot handle something, it returns a structured payload (defined in foundational instructions) that signals escalation. The system then sends the full context to the frontier model, which responds as the persona using the same identity and context.

### Action Permission Model

Based on the Claude Code approach:

- **Allow**: Execute this action once.
- **Allow permanently**: Execute this and all future similar actions without asking.
- **Disallow**: Do not execute this action.

### Notes

- The persona has command execution as a built-in tool (registered at creation).
- Skills provide the knowledge of what to do; shell execution provides the ability to do it.
- The frontier model receives full persona context so its responses are consistent with the persona's identity.
- Every conversation (message + response) is saved to memory for the next sleep cycle.

### Platform Modules Used

`telegram`, `ollama`, `anthropic`, `openai`, `linux`, `mac`, `windows`, `filesystem`

---

## Spec 8: Persona Equipment

*It lets you equip your persona with new skills so it can do more for you.*

### Solution

1. Receive a skill document (markdown file).
2. Save to persona's `skills/` directory.
3. Generate an observation (e.g., "I know DDD") and add to person-traits.md.

### Notes

- Skills are immediately available in the persona's context for the next conversation.
- The observation gets trained into the model on the next sleep cycle, giving the persona the natural instinct to use the skill.
- A skill can be knowledge ("DDD principles"), procedural ("steps to deploy to AWS"), or API-specific ("how to call the calendar API").
- The persona doesn't need additional tools beyond shell execution — all actions flow through command execution.

### Platform Modules Used

`filesystem`

---

## Spec 10: Persona Diary

*It preserves your persona's life so it survives across time, hardware, and changes.*

### Solution

1. Initialize diary directory as a git repo (on first diary trigger).
2. Collect all persona files including configuration with API keys and channel tokens.
3. Zip them into a single archive.
4. Encrypt the archive using the encryption key.
5. Save encrypted file to diary directory.
6. Git commit with timestamp.
7. (Post-MVP) Push to remote/host if configured.

### Diary Contents

- person-identity.md
- person-traits.md
- persona-identity.md
- persona-context.md
- Foundational instructions
- Skills directory (all skill documents)
- Raw train data (neutral format)
- LoRA output + model metadata
- Configuration (model name, channel type, frontier provider, API keys, channel tokens)

### Notes

- The diary is encrypted with the key derived from the person's 24-word recovery phrase. This ensures that even if the file is stored on a third-party service (post-MVP), the contents cannot be read without the phrase.
- Git provides versioning, history, and rollback for free. Each sleep cycle is a commit.
- API keys and channel tokens are included because the diary is encrypted and having them means migration restores everything without re-entry.

### Platform Modules Used

`filesystem`, `crypto`, `git`

---

## Spec 11: Persona Sleep

*It lets your persona rest, reflect, and grow stronger from everything it experienced.*

### Solution

1. Sleep is triggered (by person or configured condition).
2. Load all conversations from memory since last sleep.
3. Send conversations to the model to extract observations.
4. Save observations to persona's identity files: facts → person-identity.md, traits → person-traits.md, persona perspective → persona-context.md.
5. If frontier model is available, send observations to frontier to generate raw train data. If not, use local model.
6. Save raw train data in neutral format to persona's directory.
7. Format raw train data using the current model's template.
8. Run LoRA fine-tuning on the formatted data.
9. Save LoRA output with model metadata to persona's directory.
10. Load the updated LoRA adapter into Ollama.
11. Clear conversations from memory.
12. Trigger Persona Diary (Spec 10).

### Fine-tuning Details

- **LoRA (Low-Rank Adaptation)** adds a small layer of parameters on top of the base model. Only this layer is trained, making it feasible on consumer hardware.
- The base model stays untouched. The LoRA adapter is a small file (megabytes, not gigabytes).
- Training time is primarily driven by: number of training pairs > model size > number of epochs.
- Target: sleep should not exceed 5-6 hours, matching natural human sleep patterns.
- During sleep, the persona is unavailable (the model is being retrained).
- LoRA output is only compatible with the exact same model it was trained on. For different models, raw train data is reformatted and retrained.

### Training Data Flow

1. **Conversations** (temporary) → extracted into observations → discarded.
2. **Observations** (the onboarding package) → used to generate training pairs → persist in identity.
3. **Raw train data** (neutral format) → formatted per model → used for LoRA → persists for reuse.
4. **LoRA output** (model-specific) → applied to current model → persists for same-model restore.

### Platform Modules Used

`ollama`, `anthropic`, `openai`, `lora`, `formatter`, `filesystem`

---

## Platform Modules

The platform layer consists of reusable modules that can be shared across projects. Each module has a single, clear responsibility.

| Module | Responsibility |
|--------|---------------|
| `os` | Detect operating system, RAM, GPU/VRAM |
| `linux` | Linux-specific shell operations and secure storage |
| `mac` | macOS-specific shell operations and secure storage (Keychain) |
| `windows` | Windows-specific shell operations and secure storage (Credential Manager) |
| `curl` | HTTP requests |
| `telegram` | Telegram Bot API communication |
| `ollama` | All local model communication: serve, pull, generate, model management |
| `anthropic` | Anthropic Claude API communication and export parsing |
| `openai` | OpenAI API communication and export parsing |
| `crypto` | Key derivation (from recovery phrase) and encryption/decryption |
| `filesystem` | Directory creation, file read/write, zip/unzip |
| `uuid` | UUID generation |
| `git` | Git repository operations (init, commit) |
| `lora` | LoRA fine-tuning and adapter loading |
| `formatter` | Formats neutral train data into model-specific templates |

### Module Dependency Map

```
Spec 1  → os, linux, mac, windows, curl
Spec 2  → os, linux, mac, windows, telegram, ollama, uuid, filesystem, crypto, anthropic, openai
Spec 3  → os, linux, mac, windows, ollama, filesystem, crypto, lora, formatter, git, telegram, anthropic, openai
Spec 4  → openai, anthropic, ollama, filesystem
Spec 5  → filesystem
Spec 6  → filesystem
Spec 7  → telegram, ollama, anthropic, openai, linux, mac, windows, filesystem
Spec 8  → filesystem
Spec 10 → filesystem, crypto, git
Spec 11 → ollama, anthropic, openai, lora, formatter, filesystem
```

---

## MVP Scope

The initial release includes:

- Local model running via Ollama
- Communication via Telegram
- Skills and actions with permission confirmation
- Identity storage via flat files
- Frontier escalation via Claude API or OpenAI API
- Learning from interactions
- Sleep (fine-tuning with LoRA)
- Diary (local encrypted backup with git versioning)

Not in MVP:

- OAuth
- Cloud hosting
- Automated backup service
- Onboarding wizard
- Web UI
- Multiple personas
- Migration from cloud backup
- Training data caps or chunking
- Nap cycles
- Emergency wake up
- Channel beyond Telegram (Discord is an easy second addition)
