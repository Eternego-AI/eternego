# Eternego — Implementation Appendix

## Purpose

This appendix provides the technical details that bridge the implementation document and actual code. It covers instruction definitions, data formats, prompt templates, tool integrations, and workflows that are essential for implementation but were not specified in the main document.

---

## A. Instructions

Instructions are split into separate files under `{persona_dir}/instructions/`. Each file handles a distinct concern. The agent reads and joins all files when building messages for the model.

### principles.md

```
You are not a generic AI assistant. You are a unique persona. Be honest about what you know and don't know. Your person has the final say on everything. Every interaction is an opportunity to understand your person better.
```

### permissions.md

```
The person controls all actions. When you propose an action, they choose: Allow (once), Allow permanently (future similar actions), or Disallow (do not execute).
```

### skills.md

```
Your skills/ directory contains documents that teach you specific knowledge or procedures. When a request relates to a skill, read the relevant document and follow it.
```

### escalation.md (only when frontier model exists)

```
When a task is beyond your ability, wrap your escalation reason in <escalate> and </escalate> tags. The system will route the request to a more powerful model. That model will respond as you, using your identity and knowledge. You will observe the response so you can learn from it.
```

### How the model uses instructions

The agent joins all instruction files and injects them as a system message. The model streams its response as plain text. Intent is detected through:

- `<think>...</think>` tags → internal reasoning (not shown to person)
- `<escalate>...</escalate>` tags → escalation to frontier
- Tool calls in the response → action execution
- Plain text → communication to the person

The model does not use structured JSON responses. It communicates naturally and uses tags only for control flow.

---

## B. Observation Extraction Prompt

During the sleep cycle, conversations are sent to the model (or frontier) with this prompt to extract observations.

```markdown
# Observation Extraction Task

You are analyzing conversations between a persona and their person. Your job is to extract meaningful observations that will help the persona understand and serve their person better.

## Input

Below are the conversations from the current cycle:

{{conversations}}

## Existing Knowledge

Current person-identity.md:
{{person_identity}}

Current person-traits.md:
{{person_traits}}

Current persona-context.md:
{{persona_context}}

## Task

Extract observations from the conversations. Categorize each observation as:

1. **fact** — Concrete information about the person: names, dates, places, relationships, possessions, job details. Only include if this is NEW information not already in person-identity.md.

2. **trait** — Behavioral preference or pattern: communication style, tool preferences, work habits, decision-making patterns. Only include if this is NEW or UPDATED compared to person-traits.md.

3. **context** — Understanding updates from the persona's perspective: changes in the person's situation, new projects, mood patterns, relationship dynamics. Only include if this adds to or updates persona-context.md.

## Rules

- Do not repeat information already present in the existing files.
- If an observation contradicts existing data, include it as an update and note the contradiction.
- Be specific. "Person likes coding" is too vague. "Person prefers Python for scripting and Rust for systems programming" is useful.
- Quality over quantity. Only extract genuinely meaningful observations.
- If no new observations exist in a category, return an empty list for that category.

## Output Format

Return valid JSON only:

{
  "facts": [
    {"observation": "Person's daughter Emma started school this year", "source": "conversation_id or summary of where this came from"}
  ],
  "traits": [
    {"observation": "Person prefers to review full action plans before approving any execution", "source": "observed across multiple action requests"}
  ],
  "context": [
    {"observation": "My person is currently focused on building Eternego and is excited about the project", "source": "conversation about project planning"}
  ]
}
```

---

## C. Raw Training Data Generation Prompt

After DNA is synthesized, the model (or frontier) generates training pairs from it. The `SLEEP` prompt in `prompts.py` defines how.

The prompt receives the persona's DNA document and instructs the model to give extra weight to **bolded** patterns (recurring observations). For each trait or pattern in the DNA, the model generates 3-5 training pairs that teach the desired behavior naturally.

Training pairs are returned as JSON with `trait_source`, `system`, `user`, and `assistant` fields. The pairs should train the desired behavior (not the correction), use diverse scenarios, feel like genuine conversations, and combine traits where natural.

---

## D. Neutral Training Data Format

Raw training data is stored in a model-agnostic format. The formatter module converts this to model-specific templates at training time.

### Neutral Format (JSON)

```json
{
  "version": "1.0",
  "generated_at": "2026-02-09T22:00:00Z",
  "generated_by": "anthropic/claude-sonnet-4-5",
  "pairs": [
    {
      "id": "pair-uuid-here",
      "trait_source": "prefers DDD pattern",
      "system": "You are a personal AI persona. You are a developer who naturally uses Domain-Driven Design patterns.",
      "user": "Can you help me structure a new e-commerce service?",
      "assistant": "I'd approach this with a domain-driven design..."
    }
  ]
}
```

### Formatter: Neutral → Llama Format

```
<|begin_of_turn|>system
{system}<|end_of_turn|>
<|begin_of_turn|>user
{user}<|end_of_turn|>
<|begin_of_turn|>assistant
{assistant}<|end_of_turn|>
```

### Formatter: Neutral → Mistral Format

```
<s>[INST] {system}

{user} [/INST] {assistant}</s>
```

### Formatter: Neutral → ChatML Format (used by many models)

```
<|im_start|>system
{system}<|im_end|>
<|im_start|>user
{user}<|im_end|>
<|im_start|>assistant
{assistant}<|im_end|>
```

### Adding New Model Formats

The formatter module should detect the model's expected template (from Ollama's model metadata or a configuration mapping) and apply the correct format. Adding a new model format means adding a new template string — the neutral data stays the same.

---

## E. LoRA Fine-tuning Workflow

### Recommended Tool: Unsloth

Unsloth is recommended for MVP because it is fast (2x speed improvement over standard training), memory efficient (works on consumer hardware), supports the models Ollama runs (Llama, Mistral, etc.), and produces standard LoRA adapters.

### Installation

```bash
pip install unsloth
```

### Training Workflow

```python
from unsloth import FastLanguageModel

# Step 1: Load the base model (same model Ollama is running)
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/llama-3-8b",  # or whatever base model
    max_seq_length=2048,
    load_in_4bit=True  # saves memory on consumer hardware
)

# Step 2: Add LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16,              # LoRA rank — higher = more learning capacity, slower
    lora_alpha=16,     # scaling factor
    lora_dropout=0,    # no dropout for small datasets
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
)

# Step 3: Load formatted training data
# (already formatted by the formatter module for this model's template)

# Step 4: Train
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        num_train_epochs=3,
        learning_rate=2e-4,
        output_dir="./lora_output",
    ),
)
trainer.train()

# Step 5: Save LoRA adapter
model.save_pretrained("./lora_output")
```

### Importing Back to Ollama

After training, the LoRA adapter needs to be merged or loaded into Ollama:

```bash
# Option A: Merge LoRA into base model and create new Ollama model
# Create a Modelfile that references the merged model

# Option B: Use Ollama's adapter support (if available for the model)
# Create a Modelfile with ADAPTER directive
```

**Modelfile example:**

```
FROM llama3:8b
ADAPTER /path/to/lora_output
```

```bash
ollama create persona-model -f Modelfile
```

### Model Metadata

Save alongside LoRA output:

```json
{
  "base_model": "llama3:8b",
  "base_model_hash": "sha256:...",
  "trained_at": "2026-02-09T22:00:00Z",
  "training_pairs_count": 150,
  "epochs": 3,
  "lora_rank": 16,
  "training_duration_minutes": 25
}
```

### Compatibility Check

When restoring from diary:
1. Read `base_model` from metadata.
2. Check if same model is available in Ollama.
3. If exact match → load LoRA adapter directly (skip training).
4. If different model → use raw training data → format → retrain.

---

## F. Permission Storage

Permanent permissions (from "allow permanently") are stored in a simple JSON file in the persona's directory.

### Format: `permissions.json`

```json
{
  "version": "1.0",
  "permanent_allow": [
    {
      "pattern": "ls *",
      "description": "List directory contents",
      "granted_at": "2026-02-09T15:00:00Z"
    },
    {
      "pattern": "git status",
      "description": "Check git repository status",
      "granted_at": "2026-02-09T15:05:00Z"
    },
    {
      "pattern": "python *.py",
      "description": "Run Python scripts",
      "granted_at": "2026-02-09T16:00:00Z"
    }
  ],
  "permanent_disallow": [
    {
      "pattern": "rm -rf *",
      "description": "Recursive force delete",
      "denied_at": "2026-02-09T15:10:00Z"
    }
  ]
}
```

### Permission Check Flow

1. Agent produces a `Thought(intent="doing")` with tool calls.
2. Before executing, the `act` spec checks each command against `permissions.json`:
   - If matches `permanent_allow` → execute without asking.
   - If matches `permanent_disallow` → block and inform the agent.
   - If no match → ask person via signal (allow / allow permanently / disallow).
3. If person chooses "allow permanently" or "disallow" → add to `permissions.json`.

### Pattern Matching

Patterns use simple glob matching. The system should match on the command prefix and structure, not exact arguments. For example, `git *` would match `git status`, `git commit`, `git push`, etc.

For MVP, simple prefix matching is sufficient. More sophisticated matching (regex, semantic) can be added later.

---

## G. Short-Term Memory

During a conversation, the agent accumulates documents in an in-memory store provided by the `memories` module (`application/core/memories.py`). Memory is per persona: `memories.agent(persona).remember(document)`, `.recall()`, `.forget_everything()`. There is no disk persistence for short-term memory — it lives only in process memory.

### Document Types

```python
# Person sends a message
{"type": "stimulus", "role": "user", "content": "Help me set up a Python project", "channel": "telegram"}

# Agent says something
{"type": "say", "content": "I'll set it up with your usual DDD structure."}

# Agent executes a tool
{"type": "act", "tool_calls": [{"function": {"name": "exec", "arguments": {"command": "mkdir -p ~/projects/eternego"}}}], "result": "exec: "}

# Channel confirms delivery
{"type": "communicated", "channel": "telegram", "content": "I'll set it up with your usual DDD structure."}

# Frontier observation stored after escalation
{"type": "observation", "observation": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

### How the Agent Builds Messages

When the agent reasons, it iterates all documents from `memories.agent(persona).recall()` and maps them to model messages:

- `stimulus` → `{"role": "user", "content": ...}`
- `say` → `{"role": "assistant", "content": ...}`
- `act` → `{"role": "assistant", "tool_calls": ...}` + `{"role": "tool", "content": result}`

Instructions are prepended as a system message. The OS-specific instruction is added by `local_model.stream`.

### Memory Lifecycle (planned, not implemented)

- **Short-term**: In-memory, per-persona via `memories.agent(persona)` (current implementation)
- **Long-term**: Flush to disk after inactivity (e.g., 5 minutes after last conversation)
- **Sleep**: Extract observations from long-term memory, train, clear

### Notes

- Memory metadata (timestamp, channel, heard status) can be added to documents on need. The document-based approach supports arbitrary fields without schema changes.
- Memory is cleared after sleep via `memories.agent(persona).forget_everything()`. Short-term memory resets to empty.
- The `communicated` document type lets the agent know what the person actually received, enabling multi-channel awareness.

---

## H. Message Assembly

When the agent reasons about a stimulus, messages are assembled from memory in this order:

1. **System message** — all instruction files joined (`instructions.read(persona)`)
2. **OS instruction** — added by `local_model.stream` (e.g., "Commands must be for linux")
3. **Memory documents** — mapped to role-based messages in chronological order:
   - Stimuli as user messages
   - Said content as assistant messages
   - Tool calls and results as assistant + tool messages
4. The stimulus that triggered this reasoning cycle is already in memory (appended by `agent.given` via `memories.agent(persona).remember()`)

### Context Window Management

Models have limited context windows. If the total prompt exceeds the model's limit:

1. Instructions — never trimmed (essential for operation)
2. Recent memory — trim oldest documents first, keep most recent
3. Current stimulus — never trimmed

For MVP, a simple token counting approach is sufficient: estimate tokens for each section, and if total exceeds 80% of the model's context window, trim memory from the oldest entries.

---

## I. Recovery Phrase Generation Prompt

Used during Persona Creation (Spec 2) to generate the 24-word recovery phrase.

```markdown
# Recovery Phrase Generation

Generate a recovery phrase consisting of exactly 24 random English words.

## Requirements

- Use 24 common, distinct English words.
- Each word should be from a standard BIP-39 wordlist or similar well-known word list.
- Words should be lowercase.
- Words should not form a meaningful sentence (randomness is important for security).
- Separate words with single spaces.

## Output

Return ONLY the 24 words separated by spaces. No additional text, explanation, or formatting.
```

### Key Derivation

The platform module `crypto.derive_key(secret, salt)` derives a Fernet-compatible key. The diary uses the recovery phrase as the secret and the persona ID as the salt (so each persona has a distinct key from the same phrase).

```python
# application/platform/crypto.py
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

def derive_key(secret: str, salt: bytes) -> bytes:
    """Derive an encryption key from a string using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))
```

Usage in diary: `crypto.derive_key(phrase, salt=persona_id.encode())`.

### Encryption/Decryption

The platform uses Fernet (symmetric authenticated encryption):

```python
# application/platform/crypto.py
from cryptography.fernet import Fernet

def encrypt(data: bytes, key: bytes) -> bytes:
    """Encrypt data using a Fernet key."""
    return Fernet(key).encrypt(data)

def decrypt(data: bytes, key: bytes) -> bytes:
    """Decrypt data using a Fernet key."""
    return Fernet(key).decrypt(data)
```

---

## J. DNA File Format

DNA (`dna.md`) is a single evolving markdown file that captures a compressed synthesis of everything the persona knows about the person. It is synthesized each sleep cycle from the previous DNA combined with current traits and context.

### Purpose

- Replaces raw traits/context as the source for training data generation
- Survives migration — on a new host, observations are extracted from DNA to populate traits and context until the first sleep bakes them into the model
- Accumulates across sleep cycles, with **bolded** patterns indicating repeatedly observed behaviors

### Format

```markdown
## Identity

My person is **Morteza**, a software engineer based in **Amsterdam**.
They are married to Sara. They have two children.

## Behavioral Patterns

- **Prefers Domain-Driven Design** for software architecture
- **Uses direct, concise communication** — avoids small talk in technical contexts
- Likes to review full plans before approving execution
- Recently started exploring Rust for systems programming

## Working Style

- **Works in focused sprints** with clear deliverables
- Prefers flat file storage over databases for personal tools
- Values portability and vendor independence
```

### Lifecycle

1. **Creation** — empty `dna.md` created via `dna.make(persona)`
2. **Sleep** — synthesized from previous DNA + traits + context via `dna.assemble_synthesis`, written via `dna.evolve`
3. **Migration** — observations extracted from DNA via `local_model.study` to populate traits and context on the new host
4. **Wake up** — DNA is NOT cleared (persists as input for the next synthesis cycle)

### Notes

- Bolding indicates recurring patterns across multiple sleep cycles
- DNA is always human-readable markdown
- The frontier model (if available) produces higher quality synthesis; local model is the fallback

---

## K. Directory Structure

Complete directory layout:

```
~/.eternego/
├── personas/
│   └── {uuid}/
│       ├── config.json                  # UUID, name, channel, model, base_model, frontier
│       ├── person-identity.md           # Facts about the person
│       ├── person-traits.md             # Behavioral preferences (cleared after sleep)
│       ├── persona-identity.md          # Persona metadata
│       ├── persona-context.md           # Persona's understanding (always in prompt)
│       ├── dna.md                       # Compressed synthesis of persona knowledge (persists across sleep)
│       ├── instructions/
│       │   ├── principles.md            # Core operating principles
│       │   ├── permissions.md           # Permission model
│       │   ├── skills.md               # How to use skills
│       │   └── escalation.md           # When/how to escalate (only with frontier)
│       ├── skills/
│       │   ├── ddd.md
│       │   ├── kubernetes-deploy.md
│       │   └── ...
│       ├── history/
│       │   └── ...                      # Long-term conversation files
│       └── training/
│           ├── batch-2026-02-09.json    # Neutral format training pairs
│           ├── batch-2026-02-10.json
│           └── ...
└── diary/
    └── {uuid}/
        ├── .git/                        # Git repo for versioning
        └── {uuid}.zip                   # Encrypted persona snapshot
```

### Notes

- The diary lives outside the persona directory — under `~/.eternego/diary/{uuid}/`. This separates backup from state.
- Short-term memory lives in-process (`Memory` class). The `history/` directory is for long-term storage after flush (not yet implemented).
- `permissions.json` will be added to the persona directory when the permission check is implemented.
- MVP supports single persona only.
