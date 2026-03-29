# Subconscious — Extract Struggles

Runs during sleep. Extracts difficulties and frustrations.

Source: `application/core/brain/mind/subconscious.py:96`

---

## System Prompt

```
# Extract Struggles

Read the conversation below. Extract difficulties or frustrations the person mentioned.

What counts:
- Problems they described clearly
- Things that stress or frustrate them
- Obstacles they are facing right now
- Anything they said is hard for them

What does NOT count: things the assistant said, mild complaints, passing remarks.

Only extract from what the person said (user messages). If they described a real difficulty even once, include it.

## Current Struggles

{existing struggles or '(none yet)'}

Merge new struggles into the list above. Keep everything that is still true. If the conversation adds nothing new, return the current struggles unchanged.

Format: one struggle per line, each starting with 'The person '. No bullets, no headers, no commentary.
```

## Audit

### Fixed: removed psychology jargon
No more "avoidance patterns," "emotional blocks," "procrastination areas." Now just: "problems they described," "things that stress them." A small model understands these.

### "a real difficulty even once"
Lowered from "recur or carry strong emotional weight." Practical threshold.
