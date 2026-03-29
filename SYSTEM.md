# Eternego — System Design

How the persona works, end to end.

## Knowledge Files

Each persona maintains knowledge files in `~/.eternego/personas/{id}/home/`.
These are human-readable, portable, and model-agnostic.

### Person Identity (`person.md`)
**What:** Permanent facts about the person — name, age, birthday, gender, location, timezone, job, family, contacts, addresses.
**Extracted from:** Conversation (user messages only).
**Used in:** `character.shape()` → conscious pipeline identity.
**Timeframe:** Permanent. Only changes when facts change.

### Person Trait (`traits.md`)
**What:** Behavioral observations about the person — communication style, preferences, temperament. Examples: "polite", "concise", "thinks deeply", "uses humor", "prefers details over summaries", "direct and to the point".
**Extracted from:** Conversation (user messages only).
**Used in:** `identity()` → conscious pipeline identity.
**Timeframe:** Stable. Evolves slowly as the persona learns more.

### Wishes (`wishes.md`)
**What:** The person's goals, dreams, and aspirations — things they want to achieve or change. Examples: "trip to Paris", "financial freedom", "launch a startup", "learn piano".
**Extracted from:** Conversation (user messages only).
**Used in:** `identity()` → conscious pipeline identity.
**Timeframe:** Long-term. The persona should proactively help achieve these.
**Note:** Not behavioral — these are strategic. A wish like "present at a conference in Paris" could trigger the persona to suggest opportunities.

### Struggles (`struggles.md`)
**What:** The person's obstacles and difficulties — things they find hard or are stuck on. Examples: "public speaking anxiety", "time management", "staying focused".
**Extracted from:** Conversation (user messages only).
**Used in:** `identity()` → conscious pipeline identity.
**Timeframe:** Long-term. The persona should proactively help overcome these.
**Note:** Not behavioral — these are strategic, like wishes but for problems.

### Persona Trait (`context.md` → should be renamed to `persona_trait.md`)
**What:** Behavioral instructions for the persona — how it should act to match the person. Derived from observing person traits and conversation patterns. Examples: "be funny and use humor", "use DDD terminology", "prefer Python", "match their concise style", "be direct, no filler", "challenge ideas when they seem incomplete".
**Extracted from:** Conversation + person traits. The subconscious observes how the person communicates and derives instructions for how the persona should behave.
**Used in:** `character.shape()` → conscious pipeline identity, and DNA synthesis for training.
**Timeframe:** Stable, evolving. This is the persona's learned personality.
**Critical distinction:** Person trait observes ("the person is concise"). Persona trait instructs ("be concise"). Person trait is input; persona trait is output.

### DNA (`dna.md`)
**What:** Compressed behavioral profile synthesized from persona trait. Used to generate fine-tuning training pairs.
**Synthesized from:** Persona trait (NOT briefing, NOT conversation summaries).
**Used for:** `generate_training_set()` → fine-tuning the local model.
**Timeframe:** Regenerated each sleep cycle from current persona trait.
**Purpose:** When fine-tuned, the model natively exhibits the persona's learned behavior without needing it in the system prompt.

## Conversation

### Live Conversation (`conversation.jsonl`)
**What:** Real-time log of the current session's dialogue.
**Format:** JSONL, each line: `{"role": "person"|"persona", "content": "...", "channel": "web"|"telegram", "time": "ISO8601"}`
**Written by:** `persona.hear()` writes person entries, `ego.say()` writes persona entries.
**Lifecycle:** Accumulates during wake. Read by subconscious during sleep. Archived to history. Cleared after archiving.

### History (`history/`)
**What:** Archived conversations from past sessions.
**Format:** One markdown file per sleep cycle: `conversation-{datetime}.md`
**Created by:** Sleep cycle archives `conversation.jsonl` content.
**Used by:** Recalling meaning (for the person to revisit past conversations).

### Briefing (`history/briefing.md`)
**What:** Index of archived conversations with recaps.
**Format:** Markdown, one line per session: `- 2026-03-29: conversation-2026-03-29.md — recap text`
**Created by:** Sleep cycle, using recap signals from completed thoughts.
**Used by:** Recalling meaning (shows the index so the model can pick which file to load).
**Not used by:** DNA synthesis. Briefing is episodic memory (what happened), not procedural memory (how to behave).

## Conscious Pipeline

Five stages run by the clock tick: realize → understand → recognize → decide → conclude.

Each stage receives the persona's identity context via `ego.identity()`:
- Character: cornerstone + values + morals + person identity + persona trait
- Situation: time, environment, schedule, notes
- Knowledge: wishes, struggles, person traits

### Stage: Realize
Route incoming signals to existing or new perception threads.

### Stage: Understand
Match a perception to a Meaning (built-in or learned).

### Stage: Recognize
Generate an initial reply to the person (acknowledgment before action). Calls `ego.say()`.

### Stage: Decide
Extract structured data, execute the meaning's action. Produces a recap signal.

### Stage: Conclude
Generate a final summary after action completes. Calls `ego.say()`.

## Sleep Cycle

1. **Settle** — wait for current tick to finish.
2. **Learn from conversation** — read `conversation.jsonl`, pass to subconscious extraction:
   - `person_identity()` — update person.md
   - `person_traits()` — update traits.md
   - `wishes()` — update wishes.md
   - `struggles()` — update struggles.md
   - `persona_trait()` — update persona trait (currently context.md)
   - `synthesize_dna()` — regenerate dna.md from persona trait
3. **Archive conversation** — save conversation.jsonl content as `history/conversation-{datetime}.md`.
4. **Build briefing** — collect recap signals from completed thoughts, append entries to `briefing.md`.
5. **Clean memory** — remove completed thoughts and their exclusive signals. In-progress work survives.
6. **Clear conversation.jsonl** — start fresh for next session.
7. **Grow** — generate training pairs from DNA, fine-tune model.
8. **Wake** — restart with clean conversation, retained in-progress memory.

## Recall

When the person asks to remember something:

1. **Understand** matches to Recalling meaning.
2. **Decide** — `path()` loads `briefing.md` (date + recap listing). Model picks a file.
3. **Run** — loads the selected history file's content, returns it to the conversation thread.
4. **Conclude** — summarizes what was found.

The model sees recaps to make an informed choice, then gets the full conversation when needed.

## Identity Composition

`ego.identity()` assembles the system prompt for every conscious pipeline call:

```
# Who You Are          ← cornerstone (immutable purpose)
# What Sustains You    ← values
# How You Act          ← morals
# The Person           ← person.md (identity facts)
# Your Personality     ← persona trait (behavioral instructions)
# Situation            ← time, environment, schedule, notes
# What They Want       ← wishes.md
# What They Struggle With ← struggles.md
# Their Traits         ← person traits (behavioral observations)
```

## Training (DNA → Fine-tune)

```
persona trait → synthesize_dna → dna.md → generate_training_set → fine-tune
```

The chain: observe person → extract person traits → derive persona trait → synthesize DNA → train.
After fine-tuning, the model natively exhibits the persona's personality. Next session's conversations reinforce or refine the traits, creating a feedback loop.

Conversation content and briefing do not feed into training. They are episodic memory for recall, not behavioral data for learning.
