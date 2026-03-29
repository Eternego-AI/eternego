# Subconscious — Extract Wishes and Dreams

Runs during sleep. Extracts goals, dreams, and things the person cares about.

Source: `application/core/brain/mind/subconscious.py:73`

---

## System Prompt

```
# Extract Wishes and Dreams

Read the conversation below. Extract what the person wants in life — their goals, dreams, and things they care deeply about.

What counts:
- Goals they mentioned: career, personal, creative
- Things they said they want to build, achieve, or change
- Values they expressed with conviction
- Directions they are clearly moving toward

What does NOT count: tasks, reminders, things the assistant said, passing comments.

Only extract from what the person said (user messages). If they stated something with conviction even once, include it.

## Current Wishes

{existing wishes or '(none yet)'}

Merge new wishes into the list above. Keep everything that is still true. If the conversation adds nothing new, return the current wishes unchanged.

Format: one wish per line, each starting with 'The person '. No bullets, no headers, no commentary.
```

## Audit

### Fixed: "with conviction even once"
Replaces "emotional weight or repetition." Clearer for a small model — if the person said it and meant it, extract it.

### "Values they expressed with conviction"
New addition. Captures things like "I believe in data ownership" without needing the person to say it twice.
