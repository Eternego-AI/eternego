# Subconscious — Synthesize DNA

Runs during sleep, after all extractions. Merges accumulated knowledge into a compressed profile.

Source: `application/core/brain/mind/subconscious.py:140`

---

## System Prompt

```
# Synthesize Profile

Merge all data below into a single compressed profile.

## Previous Profile

{previous DNA content or '(first synthesis)'}

## Traits

{traits file content or '(none)'}

## Context

{context file content or '(none)'}

## Past Conversations

{history briefing — table of file | recap pairs}

Bold patterns that appear repeatedly. Merge duplicates. Drop one-off noise.
Preserve all facts (names, dates, relationships).
Write as: 'My person prefers...', 'They work at...'.

Sections: Identity, Behavioral Patterns, Working Style, Current Focus.
Return markdown text.
```

## User Message

```
Synthesize the profile.
```

## Expected Response

Markdown profile with sections: Identity, Behavioral Patterns, Working Style, Current Focus.

---

## Audit

### This is the only prompt that WORKS in today's logs
The model produced output for synthesize_dna while all 5 extraction functions returned empty. Key difference: this prompt gives the model a simple merging task with data already formatted, not analytical extraction from conversation.

### Missing sections feed "(none)" everywhere
Today's run: traits = (none), context = (none). The only real data was the previous DNA and history briefing table. The model still managed to produce a profile from just those two sources.

### "Bold patterns" — formatting instruction
Asks for **bold** markdown on repeated patterns. Good for visual scanning later.

### History briefing table format
```
| File | Recap |
|--------|--------|
| eternego introduction-2026-03-28.md | Provided summary of disk space usage |
| free storage-2026-03-28.md | Is there anything else I can help you with right now? |
```
The recap for "free storage" looks like it's an assistant response, not a real recap. This comes from how briefing entries are saved — the recap might be capturing the wrong signal. Worth investigating separately.

### Previous DNA gets fed back
The model sees its own previous output and is told to merge it. This creates a reinforcement loop — mistakes in the previous DNA get amplified. Good when data accumulates; risky if the first synthesis was based on bad data.

### Clear structure overall
Section headers, concrete format instructions, persona-perspective writing style. The best-structured subconscious prompt.
