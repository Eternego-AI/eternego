# Subconscious — Extract What Is Happening Now

Runs during sleep. Extracts the person's current life situation.

Source: `application/core/brain/mind/subconscious.py:119`

---

## System Prompt

```
# Extract What Is Happening Now

Read the conversation below. Extract what is currently going on in the person's life.

What counts:
- Projects they are working on right now
- Events or changes happening in their life
- Their current mood or emotional state if clearly expressed
- What they are focused on or busy with

What does NOT count: permanent facts (name, job), long-term dreams, things the assistant said.

Only extract from what the person said (user messages).

## Current Context

{existing context or '(none yet)'}

Merge new context into the list above. Remove entries that seem outdated. Keep 4-12 lines max. If the conversation adds nothing new, return the current context unchanged.

Format: one statement per line, written as 'My person...' or 'I know that...'. No bullets, no headers, no commentary.
```

## Audit

### Fixed: "what chapter they are in" → "what is currently going on"
Plain language. No metaphor for a small model to misinterpret.

### Fixed: "(light context — mostly quiet season right now)" removed
Fallback text no longer in the prompt. Instead: "return the current context unchanged."
